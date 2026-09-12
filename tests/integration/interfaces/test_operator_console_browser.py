from __future__ import annotations

import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
from flask import Flask
from playwright.async_api import async_playwright
from pydantic import SecretStr
from werkzeug.serving import make_server

from capability_runner.application.operator_console import OperatorConsoleService
from capability_runner.contracts.actions import FillAction
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayResult,
)
from capability_runner.contracts.intervention import (
    InterventionRecord,
    InterventionRequest,
    ResumeValidationResult,
)
from capability_runner.contracts.operator_console import OperatorControlDescriptor
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    SemanticTargetRef,
    SurfaceSessionRef,
    SurfaceView,
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
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter
from demo_app.app import DemoScenario, create_app
from tests.fixtures.corebank_browser_profile import build_core_bank_demo_profile


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


def _profile(base_url: str) -> ApplicationProfile:
    base_profile = build_core_bank_demo_profile(f"{base_url}/")
    return base_profile.model_copy(
        update={
            "target_bindings": (
                *base_profile.target_bindings,
                BrowserTargetBinding(
                    semantic_target=_target("member.results.identity"),
                    frame=_binding(base_profile, "member.results.open").frame,
                    locator_candidates=(
                        CssLocator(
                            kind="css",
                            selector="tbody tr td:first-child",
                            structural_fallback=True,
                        ),
                    ),
                ),
            )
        }
    )


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="p4.2-operator-console",
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


def _controls() -> tuple[OperatorControlDescriptor, ...]:
    return (
        OperatorControlDescriptor(
            semantic_target="member.search.member_id",
            label="Member ID",
            action_kind="fill",
            sensitive=True,
        ),
        OperatorControlDescriptor(
            semantic_target="member.search.submit",
            label="Search",
            action_kind="click",
        ),
    )


class UnexpectedResumeValidator:
    calls = 0

    async def validate(self, record: InterventionRecord) -> ResumeValidationResult:
        self.calls += 1
        raise AssertionError("P4.2 must stop before resume validation")


class RecordingOperatorGateway:
    def __init__(self, delegate: OperatorActionGateway) -> None:
        self._delegate = delegate
        self.contexts: list[GatewayExecutionContext] = []

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        *,
        operator_id: str,
    ) -> GatewayResult:
        self.contexts.append(context)
        return await self._delegate.execute(request, context, operator_id=operator_id)


class RecordingViewProvider:
    def __init__(self, delegate: BrowserSurfaceAdapter) -> None:
        self._delegate = delegate
        self.sessions: list[SurfaceSessionRef] = []

    async def capture_view(self, session: SurfaceSessionRef) -> SurfaceView:
        self.sessions.append(session)
        return await self._delegate.capture_view(session)


@dataclass(slots=True)
class LiveConsole:
    adapter: BrowserSurfaceAdapter
    session: SurfaceSessionRef
    record: InterventionRecord
    profile: ApplicationProfile
    console: OperatorConsoleService
    gateway: RecordingOperatorGateway
    views: RecordingViewProvider
    recorder: EvidenceRecorder
    validator: UnexpectedResumeValidator


def test_real_operator_http_console_controls_same_live_browser_session(tmp_path: Path) -> None:
    demo_app = create_app(scenario=DemoScenario(mode="normal", search_delay_seconds=0.12))
    with _serve(demo_app) as demo_url, AsyncCoreRunner() as runner:

        async def prepare() -> LiveConsole:
            profile = _profile(demo_url)
            target = ProfileTarget.model_validate(
                {
                    "application": "corebank",
                    "profile": "legacy-browser",
                    "entry_url": f"{demo_url}/",
                }
            )
            adapter = BrowserSurfaceAdapter(headless=True)
            controller = SessionController()
            recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
            guard = PolicyGuard(_policy())
            automation_gateway = ActionGateway(
                policy_guard=guard,
                session_controller=controller,
                surface_adapter=adapter,
                evidence_recorder=recorder,
            )
            operator_gateway = RecordingOperatorGateway(
                OperatorActionGateway(
                    policy_guard=guard,
                    session_controller=controller,
                    surface_adapter=adapter,
                    evidence_recorder=recorder,
                )
            )
            validator = UnexpectedResumeValidator()
            manager = InterventionManager(
                session_controller=controller,
                resume_validator=validator,
                evidence_recorder=recorder,
            )
            session = await adapter.open_surface_session(profile)
            await controller.open_session(session_id="control-1", run_id="run-1")
            automated = await automation_gateway.execute(
                GatewayActionRequest(
                    action_id="automation-fill",
                    semantic_target=_target("member.search.member_id"),
                    action=FillAction(target=target, value=SecretStr("12345")),
                ),
                GatewayExecutionContext(
                    run_id="run-1",
                    control_session_id="control-1",
                    expected_generation=0,
                    surface_session=session,
                    profile=profile,
                ),
            )
            assert automated.outcome == "EXECUTED"
            requested = await manager.request_intervention(
                InterventionRequest(
                    intervention_id="intervention-1",
                    run_id="run-1",
                    control_session_id="control-1",
                    surface_session=session,
                    reason_code="OPERATOR_INPUT_REQUIRED",
                    summary="Operator must select the intended member.",
                )
            )
            assert requested.record is not None
            granted = await manager.grant_operator_control(
                "intervention-1",
                operator_id="operator-1",
                display_name="Local operator",
            )
            assert granted.outcome == "OPERATOR_CONTROLLED"
            views = RecordingViewProvider(adapter)
            console = OperatorConsoleService(
                intervention_manager=manager,
                operator_gateway=operator_gateway,
                session_reader=controller,
                surface_inspector=adapter,
                view_provider=views,
            )
            console.register_intervention(
                record=requested.record,
                profile=profile,
                operator_id="operator-1",
                controls=_controls(),
            )
            return LiveConsole(
                adapter=adapter,
                session=session,
                record=requested.record,
                profile=profile,
                console=console,
                gateway=operator_gateway,
                views=views,
                recorder=recorder,
                validator=validator,
            )

        live = runner.run(prepare())
        operator_app = create_operator_console_app(
            console=live.console,
            async_runner=runner,
        )
        try:
            with _serve(operator_app) as operator_url, httpx.Client(
                base_url=operator_url,
                timeout=10,
            ) as client:
                page = client.get("/operator/interventions/intervention-1")
                status_before = client.get("/api/interventions/intervention-1")
                view_before = client.get("/api/interventions/intervention-1/view")
                controls = client.get("/api/interventions/intervention-1/controls")

                async def operate_console() -> tuple[int, int, int, bytes]:
                    async with async_playwright() as playwright:
                        browser = await playwright.chromium.launch(headless=True)
                        operator_page = await browser.new_page(
                            viewport={"width": 1280, "height": 900}
                        )
                        try:
                            await operator_page.goto(
                                f"{operator_url}/operator/interventions/intervention-1",
                                wait_until="networkidle",
                            )
                            await operator_page.get_by_text(
                                "Operator in control",
                                exact=True,
                            ).wait_for()
                            await operator_page.locator("#browser-view:not([hidden])").wait_for()
                            member_input = operator_page.get_by_label("Member ID")
                            await member_input.fill("67890")
                            async with operator_page.expect_response("**/actions") as fill_info:
                                await operator_page.get_by_role(
                                    "button",
                                    name="Submit",
                                    exact=True,
                                ).click()
                            fill_response = await fill_info.value
                            await operator_page.get_by_label("Member ID").wait_for()
                            assert await operator_page.get_by_label("Member ID").input_value() == ""

                            async with operator_page.expect_response("**/actions") as click_info:
                                await operator_page.get_by_role(
                                    "button",
                                    name="Search",
                                    exact=True,
                                ).click()
                            click_response = await click_info.value

                            async with operator_page.expect_response(
                                "**/return-control"
                            ) as return_info:
                                await operator_page.get_by_role(
                                    "button",
                                    name="Return control",
                                    exact=True,
                                ).click()
                            return_response = await return_info.value
                            await operator_page.get_by_text(
                                "Resume validation required",
                                exact=True,
                            ).wait_for()
                            screenshot = await operator_page.screenshot(type="png")
                            return (
                                fill_response.status,
                                click_response.status,
                                return_response.status,
                                screenshot,
                            )
                        finally:
                            await browser.close()

                fill_status, click_status, return_status, operator_screenshot = runner.run(
                    operate_console()
                )
                view_after = client.get("/api/interventions/intervention-1/view")
                status_after = client.get("/api/interventions/intervention-1")

            inspection = runner.run(
                live.adapter.inspect_target(
                    live.record.surface_session,
                    _binding(live.profile, "member.results.identity"),
                )
            )

            assert page.status_code == 200
            assert "Human intervention" in page.text
            assert status_before.json()["control_state"] == "operator_controlled"
            assert controls.status_code == 200
            assert len(controls.json()["controls"]) == 2
            assert view_before.status_code == 200
            assert view_before.headers["content-type"].startswith("image/png")
            assert view_before.content.startswith(b"\x89PNG\r\n\x1a\n")
            assert fill_status == 200
            assert click_status == 200
            assert return_status == 200
            assert operator_screenshot.startswith(b"\x89PNG\r\n\x1a\n")
            assert view_after.status_code == 409
            assert view_after.json()["error"]["code"] == "INVALID_STATE"
            assert status_after.json()["state_label"] == "Resume validation required"
            assert inspection.outcome == "VISIBLE"
            assert inspection.text == "67890"
            assert live.validator.calls == 0
            assert live.record.surface_session == live.session
            assert all(context.surface_session == live.session for context in live.gateway.contexts)
            assert live.views.sessions
            assert all(session == live.session for session in live.views.sessions)
            assert list(tmp_path.rglob("*.png")) == []
            evidence = live.recorder.path.read_bytes()
            assert b"12345" not in evidence
            assert b"67890" not in evidence
        finally:
            runner.run(live.adapter.aclose())