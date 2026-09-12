from __future__ import annotations

import json
import threading
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import httpx
import pytest
from flask import Flask
from pydantic import SecretStr
from werkzeug.serving import make_server

from capability_runner.application.operator_console import OperatorConsoleService
from capability_runner.application.run_coordinator import (
    ReplayContinuationCoordinator,
    ReplayContinuationRegistry,
    ReplayContinuationResumeValidator,
)
from capability_runner.capabilities.capability_validator import (
    CapabilityValidator,
    ValidatedCapability,
)
from capability_runner.contracts.actions import FillAction
from capability_runner.contracts.capabilities import CapabilityDefinition
from capability_runner.contracts.continuation import ReplayContinuationResult
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayResult,
)
from capability_runner.contracts.intervention import InterventionRecord
from capability_runner.contracts.operator_console import OperatorControlDescriptor
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.replay import ReplayResult
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    SemanticTargetRef,
    SurfaceSessionRef,
)
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.interfaces.async_core_runner import AsyncCoreRunner
from capability_runner.interfaces.operator_http import create_operator_console_app
from capability_runner.intervention.intervention_manager import InterventionManager
from capability_runner.intervention.operator_action_gateway import OperatorActionGateway
from capability_runner.replay.replay_engine import ReplayEngine
from capability_runner.replay.snapshot_collector import SnapshotCollector
from capability_runner.replay.state_evaluator import StateEvaluator
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter
from demo_app.app import DemoScenario, create_app
from tests.fixtures.corebank_browser_profile import build_core_bank_demo_profile

CAPABILITY_FIXTURE = Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json")


@contextmanager
def _serve(app: Flask) -> Generator[str, None, None]:
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _target(value: str) -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def _binding(profile: ApplicationProfile, target: str) -> BrowserTargetBinding:
    return next(
        binding
        for binding in profile.target_bindings
        if binding.semantic_target == _target(target)
    )


def _capability() -> ValidatedCapability:
    payload = json.loads(CAPABILITY_FIXTURE.read_text(encoding="utf-8"))
    return CapabilityValidator().validate(CapabilityDefinition.model_validate(payload))


def _automation_policy() -> PolicyDefinition:
    context = TrustedApplicationProfile(application="corebank", profile="legacy-browser")
    return PolicyDefinition(
        policy_id="p4.3-automation",
        version="1",
        allowed_contexts=(context,),
        rules=(
            FillPolicyRule(
                rule_id="fill-member-id",
                effect="ALLOW",
                semantic_target=_target("member.search.member_id"),
            ),
            ClickPolicyRule(
                rule_id="search",
                effect="ALLOW",
                semantic_target=_target("member.search.submit"),
            ),
            ClickPolicyRule(
                rule_id="open-result",
                effect="ALLOW",
                semantic_target=_target("member.results.open"),
            ),
            ClickPolicyRule(
                rule_id="approve-savings",
                effect="REQUIRE_APPROVAL",
                semantic_target=_target("member.accounts.savings"),
            ),
        ),
    )


def _operator_policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="p4.3-operator",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            ClickPolicyRule(
                rule_id="operator-open-savings",
                effect="ALLOW",
                semantic_target=_target("member.accounts.savings"),
            ),
        ),
    )


class ExecutedAutomationCounter:
    def __init__(self, delegate: ActionGateway) -> None:
        self._delegate = delegate
        self.executed: Counter[str] = Counter()
        self.contexts: list[GatewayExecutionContext] = []

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        self.contexts.append(context)
        result = await self._delegate.execute(request, context)
        if result.outcome == "EXECUTED":
            self.executed[request.semantic_target.value] += 1
        return result


class ExecutedOperatorCounter:
    def __init__(self, delegate: OperatorActionGateway) -> None:
        self._delegate = delegate
        self.executed: Counter[str] = Counter()
        self.contexts: list[GatewayExecutionContext] = []

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        *,
        operator_id: str,
    ) -> GatewayResult:
        self.contexts.append(context)
        result = await self._delegate.execute(request, context, operator_id=operator_id)
        if result.outcome == "EXECUTED":
            self.executed[request.semantic_target.value] += 1
        return result


class RecordingSnapshotCollector:
    def __init__(self, delegate: SnapshotCollector) -> None:
        self._delegate = delegate
        self.sessions: list[SurfaceSessionRef] = []

    async def collect(
        self,
        session: SurfaceSessionRef,
        profile: ApplicationProfile,
        targets: tuple[SemanticTargetRef, ...],
    ):
        self.sessions.append(session)
        return await self._delegate.collect(session, profile, targets)


@dataclass(slots=True)
class LiveContinuation:
    adapter: BrowserSurfaceAdapter
    session: SurfaceSessionRef
    profile: ApplicationProfile
    record: InterventionRecord
    console: OperatorConsoleService
    coordinator: ReplayContinuationCoordinator
    automation_gateway: ActionGateway
    automation_counter: ExecutedAutomationCounter
    operator_counter: ExecutedOperatorCounter
    snapshots: RecordingSnapshotCollector
    recorder: EvidenceRecorder
    initial_context: GatewayExecutionContext
    initial_result: ReplayResult


def test_replay_operator_http_resume_succeeds_without_repeating_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMMA_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(variable, raising=False)
    demo_app = create_app(scenario=DemoScenario(mode="normal", search_delay_seconds=0.02))
    with _serve(demo_app) as demo_url, AsyncCoreRunner() as runner:

        async def prepare() -> LiveContinuation:
            profile = build_core_bank_demo_profile(f"{demo_url}/")
            adapter = BrowserSurfaceAdapter(headless=True)
            controller = SessionController()
            recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
            automation_gateway = ActionGateway(
                policy_guard=PolicyGuard(_automation_policy()),
                session_controller=controller,
                surface_adapter=adapter,
                evidence_recorder=recorder,
            )
            automation_counter = ExecutedAutomationCounter(automation_gateway)
            operator_counter = ExecutedOperatorCounter(
                OperatorActionGateway(
                    policy_guard=PolicyGuard(_operator_policy()),
                    session_controller=controller,
                    surface_adapter=adapter,
                    evidence_recorder=recorder,
                )
            )
            snapshots = RecordingSnapshotCollector(SnapshotCollector(adapter))
            replay_engine = ReplayEngine(
                action_gateway=cast(ActionGateway, automation_counter),
                snapshot_collector=cast(SnapshotCollector, snapshots),
                state_evaluator=StateEvaluator(),
            )
            registry = ReplayContinuationRegistry()
            validator = ReplayContinuationResumeValidator(
                registry=registry,
                replay_engine=replay_engine,
            )
            manager = InterventionManager(
                session_controller=controller,
                resume_validator=validator,
                evidence_recorder=recorder,
            )
            coordinator = ReplayContinuationCoordinator(
                registry=registry,
                intervention_manager=manager,
                replay_engine=replay_engine,
            )

            session = await adapter.open_surface_session(profile)
            await controller.open_session(session_id="control-1", run_id="run-1")
            initial_context = GatewayExecutionContext(
                run_id="run-1",
                control_session_id="control-1",
                expected_generation=0,
                surface_session=session,
                profile=profile,
            )
            capability = _capability()
            initial_result = await replay_engine.replay(
                capability,
                {"member_id": "67890"},
                initial_context,
            )
            suspended = await coordinator.suspend_for_intervention(
                intervention_id="intervention-1",
                replay_result=initial_result,
                capability=capability,
                runtime_inputs={"member_id": "67890"},
                context=initial_context,
            )
            assert suspended.intervention is not None
            granted = await manager.grant_operator_control(
                "intervention-1",
                operator_id="operator-1",
                display_name="Local operator",
            )
            assert granted.outcome == "OPERATOR_CONTROLLED"
            console = OperatorConsoleService(
                intervention_manager=manager,
                operator_gateway=operator_counter,
                session_reader=controller,
                surface_inspector=adapter,
                view_provider=adapter,
            )
            console.register_intervention(
                record=suspended.intervention,
                profile=profile,
                operator_id="operator-1",
                controls=(
                    OperatorControlDescriptor(
                        semantic_target="member.accounts.savings",
                        label="Savings",
                        action_kind="click",
                    ),
                ),
            )
            return LiveContinuation(
                adapter=adapter,
                session=session,
                profile=profile,
                record=suspended.intervention,
                console=console,
                coordinator=coordinator,
                automation_gateway=automation_gateway,
                automation_counter=automation_counter,
                operator_counter=operator_counter,
                snapshots=snapshots,
                recorder=recorder,
                initial_context=initial_context,
                initial_result=initial_result,
            )

        live = runner.run(prepare())
        operator_app = create_operator_console_app(console=live.console, async_runner=runner)
        try:
            with _serve(operator_app) as operator_url, httpx.Client(
                base_url=operator_url,
                timeout=10,
            ) as client:
                page = client.get("/operator/interventions/intervention-1")
                view = client.get("/api/interventions/intervention-1/view")
                controls = client.get("/api/interventions/intervention-1/controls")
                human_click = client.post(
                    "/api/interventions/intervention-1/actions",
                    json={
                        "semantic_target": "member.accounts.savings",
                        "action_kind": "click",
                    },
                )
                returned = client.post(
                    "/api/interventions/intervention-1/return-control"
                )

            resumed: ReplayContinuationResult = runner.run(
                live.coordinator.resume("intervention-1")
            )
            stale = runner.run(
                live.automation_gateway.execute(
                    GatewayActionRequest(
                        action_id="stale-generation-proof",
                        semantic_target=_target("member.search.member_id"),
                        action=FillAction(
                            target=ProfileTarget.model_validate(
                                {
                                    "application": "corebank",
                                    "profile": "legacy-browser",
                                    "entry_url": live.profile.entry_point,
                                }
                            ),
                            value=SecretStr("11111"),
                        ),
                    ),
                    live.initial_context,
                )
            )
            balance = runner.run(
                live.adapter.inspect_target(
                    live.session,
                    _binding(live.profile, "member.account.balance"),
                )
            )

            assert live.initial_result.reason_code == "APPROVAL_REQUIRED"
            assert live.initial_result.checkpoint is not None
            assert live.initial_result.checkpoint.blocked_step_id == "open_savings_account"
            assert page.status_code == 200
            assert view.status_code == 200
            assert view.content.startswith(b"\x89PNG\r\n\x1a\n")
            assert controls.json()["controls"][0]["semantic_target"] == (
                "member.accounts.savings"
            )
            assert human_click.status_code == 200
            assert human_click.json()["executed"] is True
            assert returned.status_code == 200
            assert returned.json()["control_state"] == "resume_requested"
            assert resumed.outcome == "SUCCESS"
            assert resumed.replay_result is not None
            assert resumed.replay_result.outputs == {
                "balance_minor_units": 98765,
                "currency": "USD",
            }
            assert resumed.generation_before == 0
            assert resumed.generation_after == 3
            assert stale.reason_code == "STALE_GENERATION"
            assert balance.text == "$987.65 USD"
            assert live.automation_counter.executed == Counter(
                {
                    "member.search.member_id": 1,
                    "member.search.submit": 1,
                    "member.results.open": 1,
                }
            )
            assert live.operator_counter.executed == Counter(
                {"member.accounts.savings": 1}
            )
            assert live.record.surface_session == live.session
            assert live.operator_counter.contexts
            assert all(
                context.surface_session == live.session
                for context in live.operator_counter.contexts
            )
            assert live.snapshots.sessions
            assert all(session == live.session for session in live.snapshots.sessions)
            assert list(tmp_path.rglob("*.png")) == []
            evidence = live.recorder.path.read_bytes()
            assert b"67890" not in evidence
            assert b"11111" not in evidence
        finally:
            runner.run(live.adapter.aclose())