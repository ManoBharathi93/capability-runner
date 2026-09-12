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
from capability_runner.contracts.intervention import (
    InterventionRecord,
    InterventionRequest,
    ResumeValidationResult,
)
from capability_runner.contracts.observations import PageObservation
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
)
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.intervention.intervention_manager import InterventionManager
from capability_runner.intervention.operator_action_gateway import OperatorActionGateway
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
        policy_id="p4.1-handoff",
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


def _binding(profile: ApplicationProfile, target: str) -> BrowserTargetBinding:
    return next(
        binding
        for binding in profile.target_bindings
        if binding.semantic_target == _target(target)
    )


def _context(
    *,
    generation: int,
    surface_session: SurfaceSessionRef,
    profile: ApplicationProfile,
) -> GatewayExecutionContext:
    return GatewayExecutionContext(
        run_id="run-1",
        control_session_id="control-1",
        expected_generation=generation,
        surface_session=surface_session,
        profile=profile,
    )


def _fill(target: ProfileTarget, action_id: str, value: str) -> GatewayActionRequest:
    return GatewayActionRequest(
        action_id=action_id,
        semantic_target=_target("member.search.member_id"),
        action=FillAction(target=target, value=SecretStr(value)),
    )


def _click(target: ProfileTarget, action_id: str, semantic_target: str) -> GatewayActionRequest:
    return GatewayActionRequest(
        action_id=action_id,
        semantic_target=_target(semantic_target),
        action=ClickAction(target=target),
    )


class FreshMemberIdentityValidator:
    def __init__(
        self,
        *,
        adapter: BrowserSurfaceAdapter,
        expected_session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> None:
        self._adapter = adapter
        self._expected_session = expected_session
        self._binding = binding
        self.inspected_session: SurfaceSessionRef | None = None
        self.inspected_text: str | None = None

    async def validate(self, record: InterventionRecord) -> ResumeValidationResult:
        self.inspected_session = record.surface_session
        inspection = await self._adapter.inspect_target(record.surface_session, self._binding)
        self.inspected_text = inspection.text
        if record.surface_session == self._expected_session and inspection.text == "67890":
            return ResumeValidationResult(
                outcome="VALID",
                reason_code="CURRENT_MEMBER_CONFIRMED",
                summary="Fresh member identity matches operator-selected state.",
            )
        return ResumeValidationResult(
            outcome="INVALID",
            reason_code="CURRENT_MEMBER_MISMATCH",
            summary="Fresh member identity does not match operator-selected state.",
        )


def test_real_browser_handoff_preserves_session_and_freshly_validates_state(
    tmp_path: Path,
) -> None:
    with _serve_demo_app() as base_url:

        async def scenario() -> tuple[
            SurfaceSessionRef, SurfaceSessionRef, SurfaceSessionRef, bytes
        ]:
            base_profile = build_core_bank_demo_profile(f"{base_url}/")
            profile = base_profile.model_copy(
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
            target = ProfileTarget.model_validate(
                {
                    "kind": "profile",
                    "application": "corebank",
                    "profile": "legacy-browser",
                    "entry_url": f"{base_url}/",
                }
            )
            adapter = BrowserSurfaceAdapter(headless=True)
            controller = SessionController()
            recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
            policy_guard = PolicyGuard(_policy())
            automation_gateway = ActionGateway(
                policy_guard=policy_guard,
                session_controller=controller,
                surface_adapter=adapter,
                evidence_recorder=recorder,
            )
            operator_gateway = OperatorActionGateway(
                policy_guard=policy_guard,
                session_controller=controller,
                surface_adapter=adapter,
                evidence_recorder=recorder,
            )

            try:
                surface_session = await adapter.open_surface_session(profile)
                await controller.open_session(session_id="control-1", run_id="run-1")
                automation_context = _context(
                    generation=0,
                    surface_session=surface_session,
                    profile=profile,
                )
                validator = FreshMemberIdentityValidator(
                    adapter=adapter,
                    expected_session=surface_session,
                    binding=_binding(profile, "member.results.identity"),
                )
                manager = InterventionManager(
                    session_controller=controller,
                    resume_validator=validator,
                    evidence_recorder=recorder,
                )

                premature_operator = await operator_gateway.execute(
                    _fill(target, "operator-before-grant", "67890"),
                    automation_context,
                    operator_id="operator-1",
                )
                automated_fill = await automation_gateway.execute(
                    _fill(target, "automation-fill", "12345"),
                    automation_context,
                )
                requested = await manager.request_intervention(
                    InterventionRequest(
                        intervention_id="intervention-1",
                        run_id="run-1",
                        control_session_id="control-1",
                        surface_session=surface_session,
                        reason_code="OPERATOR_INPUT_REQUIRED",
                        summary="Operator must select the intended member.",
                    )
                )
                granted = await manager.grant_operator_control(
                    "intervention-1",
                    operator_id="operator-1",
                    display_name="Alex",
                )
                assert granted.session_state is not None
                operator_context = _context(
                    generation=granted.session_state.control_generation,
                    surface_session=surface_session,
                    profile=profile,
                )

                blocked_automation = await automation_gateway.execute(
                    _fill(target, "automation-during-human", "11111"),
                    operator_context,
                )
                operator_fill = await operator_gateway.execute(
                    _fill(target, "operator-fill", "67890"),
                    operator_context,
                    operator_id="operator-1",
                )
                operator_search = await operator_gateway.execute(
                    _click(target, "operator-search", "member.search.submit"),
                    operator_context,
                    operator_id="operator-1",
                )

                returned = await manager.return_operator_control(
                    "intervention-1",
                    operator_id="operator-1",
                )
                resumed = await manager.complete_resume_validation("intervention-1")
                assert resumed.session_state is not None
                resumed_context = _context(
                    generation=resumed.session_state.control_generation,
                    surface_session=surface_session,
                    profile=profile,
                )
                stale_automation = await automation_gateway.execute(
                    _fill(target, "stale-automation", "33333"),
                    automation_context,
                )
                post_resume_operator = await operator_gateway.execute(
                    _fill(target, "operator-after-return", "44444"),
                    resumed_context,
                    operator_id="operator-1",
                )
                observation = await adapter.observe_surface(surface_session)

                assert premature_operator.reason_code == "DISPATCH_NOT_ALLOWED"
                assert automated_fill.outcome == "EXECUTED"
                assert requested.outcome == "INTERVENTION_REQUESTED"
                assert granted.outcome == "OPERATOR_CONTROLLED"
                assert blocked_automation.reason_code == "DISPATCH_NOT_ALLOWED"
                assert operator_fill.outcome == "EXECUTED"
                assert operator_search.outcome == "EXECUTED"
                assert returned.outcome == "RESUME_VALIDATION_REQUIRED"
                assert resumed.outcome == "RESUMED"
                assert resumed.session_state.control_generation == 3
                assert resumed.session_state.owner.kind == "automation"
                assert stale_automation.reason_code == "STALE_GENERATION"
                assert post_resume_operator.reason_code == "DISPATCH_NOT_ALLOWED"
                assert validator.inspected_text == "67890"
                assert isinstance(observation, PageObservation)
                assert "67890" in observation.visible_text
                assert requested.record is not None
                assert requested.record.surface_session == surface_session
                assert validator.inspected_session is not None
                return (
                    requested.record.surface_session,
                    validator.inspected_session,
                    surface_session,
                    recorder.path.read_bytes(),
                )
            finally:
                await adapter.aclose()

        requested_session, validated_session, final_session, evidence = asyncio.run(scenario())

    assert requested_session == validated_session == final_session
    assert b"12345" not in evidence
    assert b"67890" not in evidence