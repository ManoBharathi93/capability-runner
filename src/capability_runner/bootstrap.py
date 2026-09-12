"""Concrete composition for generated browser packages; Replay stays provider-free."""

from __future__ import annotations

from collections.abc import Mapping

from capability_runner.capabilities.capability_validator import CapabilityValidator
from capability_runner.contracts.browser_discovery import BrowserScope, CapabilityPackage
from capability_runner.contracts.gateway import GatewayExecutionContext
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    PolicyRule,
    TrustedApplicationProfile,
)
from capability_runner.contracts.replay import ReplayResult
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.replay.replay_engine import ReplayEngine
from capability_runner.replay.snapshot_collector import SnapshotCollector
from capability_runner.replay.state_evaluator import StateEvaluator
from capability_runner.surfaces.browser_observation import fingerprint
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter


async def replay_package(
    package: CapabilityPackage,
    inputs: Mapping[str, str],
    *,
    scope: BrowserScope,
    recorder: EvidenceRecorder,
    run_id: str,
) -> ReplayResult:
    adapter = BrowserSurfaceAdapter(default_timeout_ms=10_000)
    controller = SessionController()
    await controller.open_session(session_id=run_id, run_id=run_id)
    try:
        session = await adapter.open_surface_session(package.profile, browser_scope=scope)
        observation = await adapter.observe_browser(session)
        actual = fingerprint(observation.origin + observation.path + observation.title)
        if actual != package.identity.fingerprint:
            return ReplayResult.model_validate(
                {
                    "run_id": run_id,
                    "outcome": "FAILURE",
                    "reason_code": "APPLICATION_MISMATCH",
                    "summary": "Application identity does not match the stored binding.",
                    "steps_attempted": 0,
                }
            )
        context = GatewayExecutionContext(
            run_id=run_id,
            control_session_id=run_id,
            expected_generation=0,
            surface_session=session,
            profile=package.profile,
        )
        rules: dict[tuple[str, str], PolicyRule] = {}
        for step in package.capability.steps:
            kind = step.action.kind
            rule_type = FillPolicyRule if kind == "fill" else ClickPolicyRule
            rules[kind, step.action.target.value] = rule_type(
                rule_id=step.step_id[:80], effect="ALLOW", semantic_target=step.action.target
            )
        gateway = ActionGateway(
            policy_guard=PolicyGuard(
                PolicyDefinition(
                    policy_id="generated-package",
                    version="1",
                    allowed_contexts=(
                        TrustedApplicationProfile(
                            application=package.profile.application_family,
                            profile=package.profile.variant,
                        ),
                    ),
                    rules=tuple(rules.values()),
                )
            ),
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
            observation_adapter=adapter,
            browser_scope=scope,
        )
        return await ReplayEngine(
            action_gateway=gateway,
            snapshot_collector=SnapshotCollector(adapter),
            state_evaluator=StateEvaluator(),
            evidence_recorder=recorder,
        ).replay(CapabilityValidator().validate(package.capability), inputs, context)
    finally:
        await controller.stop_session(run_id)
        await adapter.aclose()
