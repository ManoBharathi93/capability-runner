from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from capability_runner.contracts.intervention import (
    InterventionRecord,
    InterventionRequest,
    ResumeValidationResult,
)
from capability_runner.contracts.sessions import SessionControllerError
from capability_runner.contracts.surfaces import SurfaceSessionRef
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.session_controller import SessionController
from capability_runner.intervention.intervention_manager import InterventionManager


class RecordingResumeValidator:
    def __init__(self, outcome: str = "VALID") -> None:
        self.outcome = outcome
        self.calls: list[InterventionRecord] = []

    async def validate(self, record: InterventionRecord) -> ResumeValidationResult:
        self.calls.append(record)
        return ResumeValidationResult.model_validate(
            {
                "outcome": self.outcome,
                "reason_code": "CURRENT_STATE_VALID" if self.outcome == "VALID" else "DRIFTED",
                "summary": "Fresh state is valid." if self.outcome == "VALID" else "State drifted.",
            }
        )


def _request() -> InterventionRequest:
    return InterventionRequest(
        intervention_id="intervention-1",
        run_id="run-1",
        control_session_id="control-1",
        surface_session=SurfaceSessionRef(surface_session_id="surface-1"),
        reason_code="OPERATOR_INPUT_REQUIRED",
        summary="Operator input is required.",
    )


async def _manager(
    tmp_path: Path,
    validator: RecordingResumeValidator | None = None,
) -> tuple[SessionController, InterventionManager, EvidenceRecorder]:
    controller = SessionController()
    await controller.open_session(session_id="control-1", run_id="run-1")
    recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
    manager = InterventionManager(
        session_controller=controller,
        resume_validator=validator or RecordingResumeValidator(),
        evidence_recorder=recorder,
    )
    return controller, manager, recorder


def test_intervention_request_pauses_and_returns_immutable_same_session_record(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        controller, manager, _ = await _manager(tmp_path)

        result = await manager.request_intervention(_request())

        assert result.outcome == "INTERVENTION_REQUESTED"
        assert result.record is not None
        assert result.record.surface_session == _request().surface_session
        assert result.record.requested_generation == 1
        assert result.session_state is not None
        assert result.session_state.control_state == "pause_requested"
        assert (await controller.get_session("control-1")).control_generation == 1
        with pytest.raises(ValidationError):
            result.record.summary = "changed"  # type: ignore[reportAttributeAccessIssue]

    asyncio.run(scenario())


def test_operator_grant_preserves_recorded_surface_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        _, manager, _ = await _manager(tmp_path)
        requested = await manager.request_intervention(_request())

        granted = await manager.grant_operator_control(
            "intervention-1",
            operator_id="operator-1",
            display_name="Alex",
        )

        assert granted.outcome == "OPERATOR_CONTROLLED"
        assert granted.record is not None
        assert requested.record is not None
        assert granted.record.surface_session is requested.record.surface_session
        assert granted.session_state is not None
        assert granted.session_state.control_generation == 2

    asyncio.run(scenario())


def test_successful_fresh_validation_restores_original_automation_owner(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        validator = RecordingResumeValidator()
        controller, manager, recorder = await _manager(tmp_path, validator)
        await manager.request_intervention(_request())
        await manager.grant_operator_control("intervention-1", operator_id="operator-1")

        returned = await manager.return_operator_control(
            "intervention-1",
            operator_id="operator-1",
        )
        resumed = await manager.complete_resume_validation("intervention-1")

        assert returned.outcome == "RESUME_VALIDATION_REQUIRED"
        assert resumed.outcome == "RESUMED"
        assert len(validator.calls) == 1
        assert validator.calls[0].surface_session == _request().surface_session
        assert resumed.session_state is not None
        assert resumed.session_state.control_generation == 3
        assert resumed.session_state.owner.kind == "automation"
        assert resumed.session_state.owner.run_id == "run-1"
        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("control-1", expected_generation=0):
                pass
        assert exc_info.value.code == "STALE_GENERATION"

        events = [
            json.loads(line)["reason_code"]
            for line in recorder.path.read_text(encoding="utf-8").splitlines()
        ]
        assert events == [
            "INTERVENTION_REQUESTED",
            "AUTOMATION_QUIESCED",
            "OPERATOR_CONTROL_GRANTED",
            "OPERATOR_CONTROL_RETURNED",
            "RESUME_VALIDATION_SUCCEEDED",
        ]

    asyncio.run(scenario())


def test_failed_fresh_validation_keeps_automation_blocked(tmp_path: Path) -> None:
    async def scenario() -> None:
        validator = RecordingResumeValidator("INVALID")
        controller, manager, _ = await _manager(tmp_path, validator)
        await manager.request_intervention(_request())
        await manager.grant_operator_control("intervention-1", operator_id="operator-1")
        await manager.return_operator_control("intervention-1", operator_id="operator-1")

        result = await manager.complete_resume_validation("intervention-1")

        assert result.outcome == "VALIDATION_FAILED"
        assert len(validator.calls) == 1
        state = await controller.get_session("control-1")
        assert state.control_state == "resume_requested"
        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch(
                "control-1",
                expected_generation=state.control_generation,
            ):
                pass
        assert exc_info.value.code == "DISPATCH_NOT_ALLOWED"

    asyncio.run(scenario())


def test_only_current_operator_can_return_control(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller, manager, _ = await _manager(tmp_path)
        await manager.request_intervention(_request())
        await manager.grant_operator_control("intervention-1", operator_id="operator-1")

        result = await manager.return_operator_control(
            "intervention-1",
            operator_id="operator-2",
        )

        assert result.outcome == "INVALID_STATE"
        assert result.reason_code == "NOT_OPERATOR_OWNER"
        assert (await controller.get_session("control-1")).control_state == "operator_controlled"

    asyncio.run(scenario())


def test_stopped_human_session_cannot_resume(tmp_path: Path) -> None:
    async def scenario() -> None:
        _, manager, recorder = await _manager(tmp_path)
        await manager.request_intervention(_request())
        await manager.grant_operator_control("intervention-1", operator_id="operator-1")

        stopped = await manager.stop_intervention("intervention-1")
        returned = await manager.return_operator_control(
            "intervention-1",
            operator_id="operator-1",
        )
        resumed = await manager.complete_resume_validation("intervention-1")

        assert stopped.outcome == "SESSION_STOPPED"
        assert returned.outcome == "SESSION_STOPPED"
        assert resumed.outcome == "SESSION_STOPPED"
        assert b"INTERVENTION_STOPPED" in recorder.path.read_bytes()

    asyncio.run(scenario())


def test_unknown_or_duplicate_intervention_fails_closed(tmp_path: Path) -> None:
    async def scenario() -> None:
        _, manager, _ = await _manager(tmp_path)

        missing = await manager.grant_operator_control("missing", operator_id="operator-1")
        first = await manager.request_intervention(_request())
        duplicate = await manager.request_intervention(_request())

        assert missing.outcome == "INVALID_STATE"
        assert first.outcome == "INTERVENTION_REQUESTED"
        assert duplicate.outcome == "INVALID_STATE"

    asyncio.run(scenario())