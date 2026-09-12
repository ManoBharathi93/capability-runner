from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from flask.testing import FlaskClient

from capability_runner.application.operator_console import OperatorConsoleService
from capability_runner.contracts.actions import ActionSpec
from capability_runner.contracts.intervention import (
    InterventionRecord,
    InterventionRequest,
    ResumeValidationResult,
)
from capability_runner.contracts.observations import ObservationSpec
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
    SurfaceActionResult,
    SurfaceFailureEvidence,
    SurfaceSessionRef,
    SurfaceView,
    TargetInspectionResult,
)
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.interfaces.async_core_runner import AsyncCoreRunner
from capability_runner.interfaces.operator_http import create_operator_console_app
from capability_runner.intervention.intervention_manager import InterventionManager
from capability_runner.intervention.operator_action_gateway import OperatorActionGateway


class ValidResumeValidator:
    async def validate(self, record: InterventionRecord) -> ResumeValidationResult:
        return ResumeValidationResult(
            outcome="VALID",
            reason_code="CURRENT_STATE_VALID",
            summary="Current state is valid.",
        )


class RecordingSurface:
    def __init__(self) -> None:
        self.action_calls: list[tuple[SurfaceSessionRef, ActionSpec, BrowserTargetBinding]] = []
        self.inspection_calls: list[tuple[SurfaceSessionRef, BrowserTargetBinding]] = []
        self.view_calls: list[SurfaceSessionRef] = []
        self.hidden_targets: set[str] = set()

    async def open_surface_session(self, profile: ApplicationProfile) -> SurfaceSessionRef:
        raise AssertionError("not used")

    async def observe_surface(self, session: SurfaceSessionRef) -> ObservationSpec:
        raise AssertionError("not used")

    async def perform_action(
        self,
        session: SurfaceSessionRef,
        action: ActionSpec,
        binding: BrowserTargetBinding,
    ) -> SurfaceActionResult:
        self.action_calls.append((session, action, binding))
        return SurfaceActionResult(
            outcome="APPLIED",
            summary="Operator action applied.",
            action=action,
            resolved_target=binding.semantic_target,
        )

    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult:
        self.inspection_calls.append((session, binding))
        outcome = (
            "NOT_VISIBLE"
            if binding.semantic_target.value in self.hidden_targets
            else "VISIBLE"
        )
        return TargetInspectionResult(
            outcome=outcome,
            target=binding.semantic_target,
            summary="Target inspection completed.",
        )

    async def capture_view(self, session: SurfaceSessionRef) -> SurfaceView:
        self.view_calls.append(session)
        return SurfaceView(
            surface_session=session,
            content=b"\x89PNG\r\n\x1a\noperator-view",
            width=1280,
            height=720,
        )

    async def capture_failure_evidence(
        self,
        session: SurfaceSessionRef,
    ) -> SurfaceFailureEvidence | None:
        raise AssertionError("not used")

    async def close_surface_session(self, session: SurfaceSessionRef) -> None:
        raise AssertionError("not used")


@dataclass(slots=True)
class Harness:
    client: FlaskClient
    runner: AsyncCoreRunner
    surface: RecordingSurface
    controller: SessionController
    recorder: EvidenceRecorder
    record: InterventionRecord


def _target(value: str) -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def _profile() -> ApplicationProfile:
    return ApplicationProfile.model_validate(
        {
            "profile_id": "corebank-demo",
            "application_family": "corebank",
            "variant": "legacy-browser",
            "entry_point": "https://example.test/",
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=_target("member.search.member_id"),
                    locator_candidates=(CssLocator(kind="css", selector="#member-id"),),
                    description="Member ID",
                ),
                BrowserTargetBinding(
                    semantic_target=_target("member.search.submit"),
                    locator_candidates=(CssLocator(kind="css", selector="#search"),),
                    description="Search",
                ),
            ],
        }
    )


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="operator-console",
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
                rule_id="submit-search",
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


@contextmanager
def _harness(tmp_path: Path, *, state: str = "operator") -> Generator[Harness, None, None]:
    runner = AsyncCoreRunner()
    surface = RecordingSurface()
    controller = SessionController()
    recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
    manager = InterventionManager(
        session_controller=controller,
        resume_validator=ValidResumeValidator(),
        evidence_recorder=recorder,
    )
    gateway = OperatorActionGateway(
        policy_guard=PolicyGuard(_policy()),
        session_controller=controller,
        surface_adapter=surface,
        evidence_recorder=recorder,
    )

    async def prepare() -> InterventionRecord:
        await controller.open_session(session_id="control-1", run_id="run-1")
        requested = await manager.request_intervention(
            InterventionRequest(
                intervention_id="intervention-1",
                run_id="run-1",
                control_session_id="control-1",
                surface_session=SurfaceSessionRef(surface_session_id="surface-1"),
                reason_code="OPERATOR_INPUT_REQUIRED",
                summary="Operator must select the intended member.",
            )
        )
        assert requested.record is not None
        await manager.grant_operator_control("intervention-1", operator_id="operator-1")
        if state == "resume":
            await manager.return_operator_control(
                "intervention-1",
                operator_id="operator-1",
            )
        elif state == "automation":
            await manager.return_operator_control(
                "intervention-1",
                operator_id="operator-1",
            )
            await manager.complete_resume_validation("intervention-1")
        elif state == "terminal":
            await manager.stop_intervention("intervention-1")
        return requested.record

    try:
        record = runner.run(prepare())
        console = OperatorConsoleService(
            intervention_manager=manager,
            operator_gateway=gateway,
            session_reader=controller,
            surface_inspector=surface,
            view_provider=surface,
        )
        console.register_intervention(
            record=record,
            profile=_profile(),
            operator_id="operator-1",
            controls=_controls(),
        )
        app = create_operator_console_app(console=console, async_runner=runner)
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield Harness(client, runner, surface, controller, recorder, record)
    finally:
        runner.close()


def test_operator_page_and_status_are_safe_and_current(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        page = harness.client.get("/operator/interventions/intervention-1")
        response = harness.client.get("/api/interventions/intervention-1")

        assert page.status_code == 200
        assert b"Human intervention" in page.data
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["intervention_id"] == "intervention-1"
        assert payload["control_state"] == "operator_controlled"
        assert payload["state_label"] == "Operator in control"
        assert payload["generation"] == 2
        assert "surface_session_id" not in payload
        assert "operator_id" not in payload


def test_unknown_intervention_returns_404(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        response = harness.client.get("/api/interventions/missing")

        assert response.status_code == 404
        assert response.get_json() == {
            "error": {
                "code": "INTERVENTION_NOT_FOUND",
                "summary": "Intervention was not found.",
            }
        }


def test_view_uses_registered_same_session_and_is_not_persisted(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        response = harness.client.get("/api/interventions/intervention-1/view")

        assert response.status_code == 200
        assert response.content_type == "image/png"
        assert response.data.startswith(b"\x89PNG\r\n\x1a\n")
        assert response.headers["Cache-Control"] == "no-store, max-age=0"
        assert harness.surface.view_calls == [harness.record.surface_session]
        assert list(tmp_path.rglob("*.png")) == []


def test_controls_include_only_visible_registered_semantic_actions(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        harness.surface.hidden_targets.add("member.search.submit")

        response = harness.client.get("/api/interventions/intervention-1/controls")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload == {
            "controls": [
                {
                    "action_kind": "fill",
                    "label": "Member ID",
                    "semantic_target": "member.search.member_id",
                    "sensitive": True,
                }
            ]
        }
        assert all(
            session == harness.record.surface_session
            for session, _ in harness.surface.inspection_calls
        )


def test_operator_action_delegates_once_with_server_owned_session(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        response = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.member_id",
                "action_kind": "fill",
                "value": "67890",
            },
        )

        assert response.status_code == 200
        assert response.get_json() == {
            "action_kind": "fill",
            "executed": True,
            "reason_code": "APPLIED",
            "semantic_target": "member.search.member_id",
            "summary": "Operator action applied.",
        }
        assert len(harness.surface.action_calls) == 1
        assert harness.surface.action_calls[0][0] == harness.record.surface_session


def test_spoofed_session_raw_selector_and_invalid_target_are_rejected(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        spoofed = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.member_id",
                "action_kind": "fill",
                "value": "67890",
                "surface_session_id": "attacker-session",
            },
        )
        selector = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.member_id",
                "action_kind": "fill",
                "value": "67890",
                "selector": "#member-id",
            },
        )
        invalid_target = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.unknown",
                "action_kind": "click",
            },
        )

        assert spoofed.status_code == 400
        assert selector.status_code == 400
        assert invalid_target.status_code == 422
        assert harness.surface.action_calls == []


def test_sensitive_fill_is_absent_from_response_and_evidence(tmp_path: Path) -> None:
    sentinel = "OPERATOR_HTTP_PRIVATE_73921"
    with _harness(tmp_path) as harness:
        response = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.member_id",
                "action_kind": "fill",
                "value": sentinel,
            },
        )

        assert response.status_code == 200
        assert sentinel.encode() not in response.data
        assert sentinel.encode() not in harness.recorder.path.read_bytes()


def test_action_is_rejected_while_automation_owns(tmp_path: Path) -> None:
    with _harness(tmp_path, state="automation") as harness:
        response = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.submit",
                "action_kind": "click",
            },
        )

        assert response.status_code == 409
        assert response.get_json()["reason_code"] == "DISPATCH_NOT_ALLOWED"
        assert harness.surface.action_calls == []


def test_return_control_moves_to_resume_validation_and_blocks_actions(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        returned = harness.client.post(
            "/api/interventions/intervention-1/return-control"
        )
        action = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.submit",
                "action_kind": "click",
            },
        )
        status = harness.client.get("/api/interventions/intervention-1")

        assert returned.status_code == 200
        assert returned.get_json()["control_state"] == "resume_requested"
        assert returned.get_json()["state_label"] == "Resume validation required"
        assert action.status_code == 409
        assert action.get_json()["reason_code"] == "DISPATCH_NOT_ALLOWED"
        assert status.get_json()["control_state"] == "resume_requested"
        assert harness.surface.action_calls == []


def test_terminal_session_rejects_action_and_view(tmp_path: Path) -> None:
    with _harness(tmp_path, state="terminal") as harness:
        action = harness.client.post(
            "/api/interventions/intervention-1/actions",
            json={
                "semantic_target": "member.search.submit",
                "action_kind": "click",
            },
        )
        view = harness.client.get("/api/interventions/intervention-1/view")

        assert action.status_code == 409
        assert action.get_json()["reason_code"] == "SESSION_STOPPED"
        assert view.status_code == 409
        assert view.get_json()["error"]["code"] == "SESSION_STOPPED"
        assert harness.surface.action_calls == []
        assert harness.surface.view_calls == []


def test_stop_endpoint_moves_session_to_terminal(tmp_path: Path) -> None:
    with _harness(tmp_path) as harness:
        response = harness.client.post("/api/interventions/intervention-1/stop")
        status = harness.client.get("/api/interventions/intervention-1")

        assert response.status_code == 200
        assert response.get_json()["control_state"] == "terminal"
        assert status.get_json()["state_label"] == "Session stopped"