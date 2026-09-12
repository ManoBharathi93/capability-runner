from __future__ import annotations

import asyncio
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from pydantic import SecretStr
from werkzeug.serving import make_server

from capability_runner.contracts.actions import ClickAction, FillAction
from capability_runner.contracts.gateway import GatewayActionRequest, GatewayExecutionContext
from capability_runner.contracts.observations import PageObservation
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.surfaces import SemanticTargetRef
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter
from demo_app.app import DemoScenario, create_app
from tests.fixtures.corebank_browser_profile import build_core_bank_demo_profile


@contextmanager
def _serve_demo_app() -> Generator[str, None, None]:
    server = make_server(
        "127.0.0.1",
        0,
        create_app(scenario=DemoScenario(mode="normal", search_delay_seconds=0.12)),
    )
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


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="corebank-gateway",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            FillPolicyRule(
                rule_id="fill-member-id",
                effect="ALLOW",
                semantic_target=_target("member.search.member_id"),
            ),
            ClickPolicyRule(
                rule_id="submit-member-search",
                effect="ALLOW",
                semantic_target=_target("member.search.submit"),
            ),
        ),
    )


def test_gateway_executes_authorized_browser_workflow_and_records_evidence(tmp_path: Path) -> None:
    with _serve_demo_app() as base_url:

        async def scenario() -> tuple[str, bytes]:
            profile = build_core_bank_demo_profile(f"{base_url}/")
            adapter = BrowserSurfaceAdapter(headless=True)
            controller = SessionController()
            recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
            gateway = ActionGateway(
                policy_guard=PolicyGuard(_policy()),
                session_controller=controller,
                surface_adapter=adapter,
                evidence_recorder=recorder,
            )
            target = ProfileTarget.model_validate(
                {
                    "kind": "profile",
                    "application": "corebank",
                    "profile": "legacy-browser",
                    "entry_url": f"{base_url}/",
                }
            )
            try:
                surface_session = await adapter.open_surface_session(profile)
                await controller.open_session(session_id="control-1", run_id="run-1")
                context = GatewayExecutionContext(
                    run_id="run-1",
                    control_session_id="control-1",
                    expected_generation=0,
                    surface_session=surface_session,
                    profile=profile,
                )
                fill_result = await gateway.execute(
                    GatewayActionRequest(
                        action_id="fill-1",
                        semantic_target=_target("member.search.member_id"),
                        action=FillAction(target=target, value=SecretStr("12345")),
                    ),
                    context,
                )
                click_result = await gateway.execute(
                    GatewayActionRequest(
                        action_id="click-1",
                        semantic_target=_target("member.search.submit"),
                        action=ClickAction(target=target),
                    ),
                    context,
                )
                observation = await adapter.observe_surface(surface_session)
                assert fill_result.outcome == "EXECUTED"
                assert click_result.outcome == "EXECUTED"
                assert isinstance(observation, PageObservation)
                return observation.visible_text, recorder.path.read_bytes()
            finally:
                await adapter.aclose()

        visible_text, evidence = asyncio.run(scenario())

    assert "Avery Morgan" in visible_text
    assert b"12345" not in evidence
    assert b"member.search.member_id" in evidence
    assert b"member.search.submit" in evidence


def test_gateway_denied_close_action_does_not_render_destructive_simulation(
    tmp_path: Path,
) -> None:
    with _serve_demo_app() as base_url:

        async def scenario() -> tuple[str, str]:
            profile = build_core_bank_demo_profile(f"{base_url}/")
            adapter = BrowserSurfaceAdapter(headless=True)
            controller = SessionController()
            recorder = EvidenceRecorder(tmp_path / "evidence-denied", run_id="run-1")
            policy = PolicyDefinition(
                policy_id="corebank-gateway-deny-close",
                version="1",
                allowed_contexts=(
                    TrustedApplicationProfile(
                        application="corebank",
                        profile="legacy-browser",
                    ),
                ),
                rules=(
                    ClickPolicyRule(
                        rule_id="deny-close",
                        effect="DENY",
                        semantic_target=_target("member.account.close"),
                    ),
                ),
            )
            gateway = ActionGateway(
                policy_guard=PolicyGuard(policy),
                session_controller=controller,
                surface_adapter=adapter,
                evidence_recorder=recorder,
            )
            target = ProfileTarget.model_validate(
                {
                    "kind": "profile",
                    "application": "corebank",
                    "profile": "legacy-browser",
                    "entry_url": f"{base_url}/",
                }
            )
            try:
                surface_session = await adapter.open_surface_session(profile)
                await controller.open_session(session_id="control-1", run_id="run-1")
                context = GatewayExecutionContext(
                    run_id="run-1",
                    control_session_id="control-1",
                    expected_generation=0,
                    surface_session=surface_session,
                    profile=profile,
                )
                before = await adapter.observe_surface(surface_session)
                result = await gateway.execute(
                    GatewayActionRequest(
                        action_id="close-1",
                        semantic_target=_target("member.account.close"),
                        action=ClickAction(target=target),
                    ),
                    context,
                )
                after = await adapter.observe_surface(surface_session)
                assert result.outcome == "DENIED"
                assert isinstance(before, PageObservation)
                assert isinstance(after, PageObservation)
                return before.visible_text, after.visible_text
            finally:
                await adapter.aclose()

        before_text, after_text = asyncio.run(scenario())

    assert before_text == after_text
    assert "no changes have been made" not in after_text.casefold()