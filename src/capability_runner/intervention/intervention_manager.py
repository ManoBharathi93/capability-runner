"""Coordinate same-session ownership handoff without owning the state machine."""

from __future__ import annotations

from typing import Protocol

from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.intervention import (
    InterventionRecord,
    InterventionRequest,
    InterventionResult,
    ResumeValidationResult,
)
from capability_runner.contracts.sessions import (
    AutomationOwner,
    OperatorOwner,
    SessionControllerError,
)
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interaction.session_controller import SessionController


class EvidenceWriter(Protocol):
    def record(
        self,
        event: EvidenceEvent,
        *,
        redaction_context: RedactionContext | None = None,
    ) -> object: ...


class ResumeValidator(Protocol):
    async def validate(self, record: InterventionRecord) -> ResumeValidationResult: ...


class InterventionManager:
    def __init__(
        self,
        *,
        session_controller: SessionController,
        resume_validator: ResumeValidator,
        evidence_recorder: EvidenceWriter,
    ) -> None:
        self._session_controller = session_controller
        self._resume_validator = resume_validator
        self._evidence_recorder = evidence_recorder
        self._records: dict[str, InterventionRecord] = {}

    async def request_intervention(self, request: InterventionRequest) -> InterventionResult:
        current = await self._session_controller.get_session(request.control_session_id)
        if not isinstance(current.owner, AutomationOwner) or current.owner.run_id != request.run_id:
            return self._result(
                "INVALID_STATE",
                "INVALID_STATE_TRANSITION",
                "Intervention requester does not own automation control.",
            )
        if request.intervention_id in self._records:
            return self._result(
                "INVALID_STATE",
                "INVALID_STATE_TRANSITION",
                "Intervention identifier already exists.",
            )
        try:
            state = await self._session_controller.request_pause(request.control_session_id)
        except SessionControllerError as error:
            return self._session_error(error)

        record = InterventionRecord(
            **request.model_dump(),
            requested_generation=state.control_generation,
        )
        self._records[record.intervention_id] = record
        self._record_event("INTERVENTION_REQUESTED", record, state.control_generation)
        return self._result(
            "INTERVENTION_REQUESTED",
            "INTERVENTION_REQUESTED",
            "Automation pause requested.",
            record,
            state,
        )

    async def grant_operator_control(
        self,
        intervention_id: str,
        *,
        operator_id: str,
        display_name: str | None = None,
    ) -> InterventionResult:
        record = self._record(intervention_id)
        if record is None:
            return self._unknown_intervention()
        try:
            state = await self._session_controller.grant_human_control(
                record.control_session_id,
                operator_id=operator_id,
                display_name=display_name,
            )
        except SessionControllerError as error:
            if error.code == "ACTION_IN_FLIGHT":
                return self._result(
                    "WAITING_FOR_QUIESCENCE",
                    error.code,
                    error.summary,
                    record,
                )
            return self._session_error(error, record)

        self._record_event("AUTOMATION_QUIESCED", record, state.control_generation)
        self._record_event("OPERATOR_CONTROL_GRANTED", record, state.control_generation)
        return self._result(
            "OPERATOR_CONTROLLED",
            "OPERATOR_CONTROL_GRANTED",
            "Operator owns the live session.",
            record,
            state,
        )

    async def return_operator_control(
        self,
        intervention_id: str,
        *,
        operator_id: str,
    ) -> InterventionResult:
        record = self._record(intervention_id)
        if record is None:
            return self._unknown_intervention()
        current = await self._session_controller.get_session(record.control_session_id)
        if current.control_state == "terminal":
            self._record_event(
                "INTERVENTION_STOPPED",
                record,
                current.control_generation,
            )
            return self._result(
                "SESSION_STOPPED",
                "SESSION_STOPPED",
                "Intervention session is terminal.",
                record,
                current,
            )
        if not isinstance(current.owner, OperatorOwner) or current.owner.operator_id != operator_id:
            return self._result(
                "INVALID_STATE",
                "NOT_OPERATOR_OWNER",
                "Only the current operator may return control.",
                record,
                current,
            )
        try:
            state = await self._session_controller.return_control_for_resume_check(
                record.control_session_id
            )
        except SessionControllerError as error:
            if error.code == "ACTION_IN_FLIGHT":
                return self._result(
                    "WAITING_FOR_QUIESCENCE",
                    error.code,
                    error.summary,
                    record,
                    current,
                )
            return self._session_error(error, record)

        self._record_event("OPERATOR_CONTROL_RETURNED", record, state.control_generation)
        return self._result(
            "RESUME_VALIDATION_REQUIRED",
            "RESUME_VALIDATION_REQUIRED",
            "Fresh state validation is required before automation resumes.",
            record,
            state,
        )

    async def complete_resume_validation(self, intervention_id: str) -> InterventionResult:
        record = self._record(intervention_id)
        if record is None:
            return self._unknown_intervention()
        current = await self._session_controller.get_session(record.control_session_id)
        if current.control_state == "terminal":
            self._record_event(
                "INTERVENTION_STOPPED",
                record,
                current.control_generation,
            )
            return self._result(
                "SESSION_STOPPED",
                "SESSION_STOPPED",
                "Intervention session is terminal.",
                record,
                current,
            )
        if current.control_state != "resume_requested":
            return self._result(
                "INVALID_STATE",
                "INVALID_STATE_TRANSITION",
                "Resume validation is not currently allowed.",
                record,
                current,
            )

        validation = await self._resume_validator.validate(record)
        if validation.outcome == "INVALID":
            self._record_event(
                "RESUME_VALIDATION_FAILED",
                record,
                current.control_generation,
                validation.reason_code,
            )
            return self._result(
                "VALIDATION_FAILED",
                validation.reason_code,
                validation.summary,
                record,
                current,
            )

        try:
            state = await self._session_controller.resume_automation_after_validation(
                record.control_session_id
            )
        except SessionControllerError as error:
            return self._session_error(error, record)
        self._record_event("RESUME_VALIDATION_SUCCEEDED", record, state.control_generation)
        return self._result(
            "RESUMED",
            "RESUME_VALIDATION_SUCCEEDED",
            "Automation ownership restored after fresh validation.",
            record,
            state,
        )

    async def stop_intervention(self, intervention_id: str) -> InterventionResult:
        record = self._record(intervention_id)
        if record is None:
            return self._unknown_intervention()
        state = await self._session_controller.stop_session(record.control_session_id)
        self._record_event("INTERVENTION_STOPPED", record, state.control_generation)
        return self._result(
            "SESSION_STOPPED",
            "SESSION_STOPPED",
            "Intervention session is terminal.",
            record,
            state,
        )

    def _record_event(
        self,
        event_name: str,
        record: InterventionRecord,
        generation: int,
        detail_code: str | None = None,
    ) -> None:
        self._evidence_recorder.record(
            EvidenceEvent(
                event_type="intervention",
                component="intervention-manager",
                run_id=record.run_id,
                session_id=record.control_session_id,
                outcome=event_name.casefold(),
                reason_code=event_name,
                summary=event_name.replace("_", " ").title(),
                metadata={
                    "intervention_id": record.intervention_id,
                    "surface_session_id": record.surface_session.surface_session_id,
                    "control_generation": generation,
                    "detail_code": detail_code,
                },
            ),
            redaction_context=RedactionContext(),
        )

    def _record(self, intervention_id: str) -> InterventionRecord | None:
        return self._records.get(intervention_id)

    @staticmethod
    def _result(
        outcome: str,
        reason_code: str,
        summary: str,
        record: InterventionRecord | None = None,
        state: object | None = None,
    ) -> InterventionResult:
        return InterventionResult.model_validate(
            {
                "outcome": outcome,
                "record": record,
                "session_state": state,
                "reason_code": reason_code,
                "summary": summary,
            }
        )

    def _session_error(
        self,
        error: SessionControllerError,
        record: InterventionRecord | None = None,
    ) -> InterventionResult:
        if error.code == "SESSION_STOPPED":
            if record is not None:
                self._record_event("INTERVENTION_STOPPED", record, 0, error.code)
            outcome = "SESSION_STOPPED"
        elif error.code == "STALE_GENERATION":
            outcome = "STALE_GENERATION"
        else:
            outcome = "INVALID_STATE"
        return self._result(outcome, error.code, error.summary, record)

    @staticmethod
    def _unknown_intervention() -> InterventionResult:
        return InterventionManager._result(
            "INVALID_STATE",
            "INVALID_STATE_TRANSITION",
            "Intervention does not exist.",
        )
