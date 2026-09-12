from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import SecretStr

from capability_runner.contracts.actions import ActionSpec, FillAction
from capability_runner.contracts.gateway import GatewayActionRequest, GatewayExecutionContext
from capability_runner.contracts.intervention import (
    InterventionRecord,
    InterventionRequest,
    ResumeValidationResult,
)
from capability_runner.contracts.observations import ObservationSpec
from capability_runner.contracts.policy import (
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
    TargetInspectionResult,
)
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.intervention.intervention_manager import InterventionManager
from capability_runner.intervention.operator_action_gateway import OperatorActionGateway


class TwoActionBarrierAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.started = (asyncio.Event(), asyncio.Event())
        self.release = (asyncio.Event(), asyncio.Event())

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
        index = self.calls
        self.calls += 1
        self.started[index].set()
        await self.release[index].wait()
        return SurfaceActionResult(
            outcome="APPLIED",
            summary="Applied.",
            action=action,
            resolved_target=binding.semantic_target,
        )

    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult:
        raise AssertionError("not used")

    async def capture_failure_evidence(
        self,
        session: SurfaceSessionRef,
    ) -> SurfaceFailureEvidence | None:
        raise AssertionError("not used")

    async def close_surface_session(self, session: SurfaceSessionRef) -> None:
        raise AssertionError("not used")


class ValidResumeValidator:
    async def validate(self, record: InterventionRecord) -> ResumeValidationResult:
        return ResumeValidationResult(
            outcome="VALID",
            reason_code="CURRENT_STATE_VALID",
            summary="Current state is valid.",
        )


def _target() -> SemanticTargetRef:
    return SemanticTargetRef(value="member.search.member_id")


def _profile() -> ApplicationProfile:
    return ApplicationProfile.model_validate(
        {
            "profile_id": "profile",
            "application_family": "corebank",
            "variant": "legacy-browser",
            "entry_point": "https://example.test/",
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=_target(),
                    locator_candidates=(CssLocator(kind="css", selector="#member-id"),),
                )
            ],
        }
    )


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="handoff",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            FillPolicyRule(
                rule_id="fill",
                effect="ALLOW",
                semantic_target=_target(),
            ),
        ),
    )


def _request(action_id: str, value: str) -> GatewayActionRequest:
    return GatewayActionRequest(
        action_id=action_id,
        semantic_target=_target(),
        action=FillAction.model_construct(target=None, value=SecretStr(value)),
    )


def _context(generation: int) -> GatewayExecutionContext:
    return GatewayExecutionContext(
        run_id="run-1",
        control_session_id="control-1",
        expected_generation=generation,
        surface_session=SurfaceSessionRef(surface_session_id="surface-1"),
        profile=_profile(),
    )


def test_bidirectional_dispatch_remains_protected_during_handoff(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller = SessionController()
        await controller.open_session(session_id="control-1", run_id="run-1")
        adapter = TwoActionBarrierAdapter()
        recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
        policy = PolicyGuard(_policy())
        automation = ActionGateway(
            policy_guard=policy,
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
        )
        operator = OperatorActionGateway(
            policy_guard=policy,
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
        )
        manager = InterventionManager(
            session_controller=controller,
            resume_validator=ValidResumeValidator(),
            evidence_recorder=recorder,
        )

        first = asyncio.create_task(
            automation.execute(_request("automation-first", "12345"), _context(0))
        )
        await adapter.started[0].wait()
        requested = await manager.request_intervention(
            InterventionRequest(
                intervention_id="intervention-1",
                run_id="run-1",
                control_session_id="control-1",
                surface_session=_context(0).surface_session,
                reason_code="OPERATOR_INPUT_REQUIRED",
                summary="Operator input is required.",
            )
        )

        queued_automation_started = asyncio.Event()
        queued_operator_started = asyncio.Event()

        async def queued_automation():
            queued_automation_started.set()
            return await automation.execute(
                _request("automation-queued", "11111"),
                _context(1),
            )

        async def queued_operator():
            queued_operator_started.set()
            return await operator.execute(
                _request("operator-too-early", "22222"),
                _context(1),
                operator_id="operator-1",
            )

        queued_automation_task = asyncio.create_task(queued_automation())
        queued_operator_task = asyncio.create_task(queued_operator())
        await queued_automation_started.wait()
        await queued_operator_started.wait()
        waiting = await manager.grant_operator_control(
            "intervention-1",
            operator_id="operator-1",
        )

        assert requested.outcome == "INTERVENTION_REQUESTED"
        assert waiting.outcome == "WAITING_FOR_QUIESCENCE"
        assert adapter.calls == 1

        adapter.release[0].set()
        assert (await first).outcome == "EXECUTED"
        assert (await queued_automation_task).reason_code in {
            "STALE_GENERATION",
            "DISPATCH_NOT_ALLOWED",
        }
        assert (await queued_operator_task).reason_code == "DISPATCH_NOT_ALLOWED"

        granted = await manager.grant_operator_control(
            "intervention-1",
            operator_id="operator-1",
        )
        assert granted.outcome == "OPERATOR_CONTROLLED"
        assert granted.session_state is not None
        operator_generation = granted.session_state.control_generation

        operator_task = asyncio.create_task(
            operator.execute(
                _request("operator-active", "67890"),
                _context(operator_generation),
                operator_id="operator-1",
            )
        )
        await adapter.started[1].wait()

        blocked_automation_started = asyncio.Event()

        async def blocked_automation():
            blocked_automation_started.set()
            return await automation.execute(
                _request("automation-during-human", "33333"),
                _context(operator_generation),
            )

        blocked_automation_task = asyncio.create_task(blocked_automation())
        await blocked_automation_started.wait()
        return_waiting = await manager.return_operator_control(
            "intervention-1",
            operator_id="operator-1",
        )

        assert return_waiting.outcome == "WAITING_FOR_QUIESCENCE"
        assert adapter.calls == 2

        adapter.release[1].set()
        assert (await operator_task).outcome == "EXECUTED"
        assert (await blocked_automation_task).reason_code == "DISPATCH_NOT_ALLOWED"

        returned = await manager.return_operator_control(
            "intervention-1",
            operator_id="operator-1",
        )
        resumed = await manager.complete_resume_validation("intervention-1")

        assert returned.outcome == "RESUME_VALIDATION_REQUIRED"
        assert resumed.outcome == "RESUMED"
        assert resumed.session_state is not None
        assert resumed.session_state.control_generation == 3

    asyncio.run(scenario())