"""Thin application coordinator for one local same-session operator console."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from capability_runner.contracts.actions import ClickAction, FillAction
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayResult,
)
from capability_runner.contracts.intervention import InterventionRecord, InterventionResult
from capability_runner.contracts.operator_console import (
    OperatorActionResponse,
    OperatorActionSubmission,
    OperatorControlDescriptor,
    OperatorInterventionStatus,
    OperatorTransitionResponse,
)
from capability_runner.contracts.sessions import OperatorOwner, SessionState
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    SemanticTargetRef,
    SurfaceSessionRef,
    SurfaceView,
    TargetInspectionResult,
)
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.surfaces.surface_view import SurfaceViewProvider


class OperatorActionExecutor(Protocol):
    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        *,
        operator_id: str,
    ) -> GatewayResult: ...


class InterventionCoordinator(Protocol):
    async def return_operator_control(
        self,
        intervention_id: str,
        *,
        operator_id: str,
    ) -> InterventionResult: ...

    async def stop_intervention(self, intervention_id: str) -> InterventionResult: ...


class SessionStateReader(Protocol):
    async def get_session(self, session_id: str) -> SessionState: ...


class SurfaceInspector(Protocol):
    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult: ...


class OperatorConsoleError(RuntimeError):
    def __init__(self, code: str, summary: str, http_status: int) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.http_status = http_status


@dataclass(frozen=True, slots=True)
class _Registration:
    record: InterventionRecord
    profile: ApplicationProfile
    operator_id: str
    controls: tuple[OperatorControlDescriptor, ...]


class OperatorConsoleService:
    def __init__(
        self,
        *,
        intervention_manager: InterventionCoordinator,
        operator_gateway: OperatorActionExecutor,
        session_reader: SessionStateReader,
        surface_inspector: SurfaceInspector,
        view_provider: SurfaceViewProvider,
    ) -> None:
        self._intervention_manager = intervention_manager
        self._operator_gateway = operator_gateway
        self._session_reader = session_reader
        self._surface_inspector = surface_inspector
        self._view_provider = view_provider
        self._registrations: dict[str, _Registration] = {}

    def register_intervention(
        self,
        *,
        record: InterventionRecord,
        profile: ApplicationProfile,
        operator_id: str,
        controls: tuple[OperatorControlDescriptor, ...],
    ) -> None:
        if record.intervention_id in self._registrations:
            raise ValueError("intervention is already registered")
        if not operator_id:
            raise ValueError("operator_id must not be empty")
        profile_targets = {binding.semantic_target.value for binding in profile.target_bindings}
        if not controls:
            raise ValueError("at least one operator control is required")
        if any(control.semantic_target not in profile_targets for control in controls):
            raise ValueError("operator controls must use trusted profile targets")
        control_keys = {(control.semantic_target, control.action_kind) for control in controls}
        if len(control_keys) != len(controls):
            raise ValueError("operator controls must be unique")
        self._registrations[record.intervention_id] = _Registration(
            record=record,
            profile=profile,
            operator_id=operator_id,
            controls=controls,
        )

    async def get_status(self, intervention_id: str) -> OperatorInterventionStatus:
        registration = self._registration(intervention_id)
        state = await self._session_reader.get_session(registration.record.control_session_id)
        return OperatorInterventionStatus(
            intervention_id=registration.record.intervention_id,
            reason=registration.record.summary,
            reason_code=registration.record.reason_code,
            control_state=state.control_state,
            state_label=self._state_label(state.control_state),
            owner_kind=state.owner.kind,
            generation=state.control_generation,
            surface_kind=registration.record.surface_session.surface_kind,
        )

    async def get_available_controls(
        self,
        intervention_id: str,
    ) -> tuple[OperatorControlDescriptor, ...]:
        registration = self._registration(intervention_id)
        state = await self._session_reader.get_session(registration.record.control_session_id)
        self._require_operator_control(state, registration.operator_id)
        bindings = {
            binding.semantic_target.value: binding
            for binding in registration.profile.target_bindings
        }
        visible: list[OperatorControlDescriptor] = []
        for control in registration.controls:
            try:
                inspection = await self._surface_inspector.inspect_target(
                    registration.record.surface_session,
                    bindings[control.semantic_target],
                )
            except Exception:
                continue
            if inspection.outcome == "VISIBLE":
                visible.append(control)
        return tuple(visible)

    async def capture_view(self, intervention_id: str) -> SurfaceView:
        registration = self._registration(intervention_id)
        state = await self._session_reader.get_session(registration.record.control_session_id)
        self._require_operator_control(state, registration.operator_id)
        try:
            view = await self._view_provider.capture_view(registration.record.surface_session)
        except Exception as error:
            raise OperatorConsoleError(
                "VIEW_UNAVAILABLE",
                "Current browser view is unavailable.",
                503,
            ) from error
        if view.surface_session != registration.record.surface_session:
            raise OperatorConsoleError(
                "VIEW_SESSION_MISMATCH",
                "Surface view did not match the intervention session.",
                500,
            )
        return view

    async def execute_action(
        self,
        intervention_id: str,
        submission: OperatorActionSubmission,
    ) -> OperatorActionResponse:
        registration = self._registration(intervention_id)
        control = next(
            (
                item
                for item in registration.controls
                if item.semantic_target == submission.semantic_target
                and item.action_kind == submission.action_kind
            ),
            None,
        )
        if control is None:
            raise OperatorConsoleError(
                "OPERATOR_CONTROL_NOT_ALLOWED",
                "Requested semantic action is not available to the operator.",
                422,
            )

        state = await self._session_reader.get_session(registration.record.control_session_id)
        target = ProfileTarget(
            application=registration.profile.application_family,
            profile=registration.profile.variant,
            entry_url=registration.profile.entry_point,
        )
        if submission.action_kind == "fill":
            if submission.value is None:
                raise OperatorConsoleError(
                    "INVALID_OPERATOR_ACTION",
                    "Fill action requires a value.",
                    400,
                )
            action = FillAction(target=target, value=submission.value)
        else:
            action = ClickAction(target=target)

        request = GatewayActionRequest(
            action_id=f"operator-{uuid4().hex}",
            semantic_target=SemanticTargetRef(value=submission.semantic_target),
            action=action,
        )
        context = GatewayExecutionContext(
            run_id=registration.record.run_id,
            control_session_id=registration.record.control_session_id,
            expected_generation=state.control_generation,
            surface_session=registration.record.surface_session,
            profile=registration.profile,
        )
        result = await self._operator_gateway.execute(
            request,
            context,
            operator_id=registration.operator_id,
        )
        return OperatorActionResponse(
            executed=result.outcome == "EXECUTED",
            semantic_target=submission.semantic_target,
            action_kind=submission.action_kind,
            reason_code=result.reason_code,
            summary=result.summary,
        )

    async def return_control(self, intervention_id: str) -> OperatorTransitionResponse:
        registration = self._registration(intervention_id)
        result = await self._intervention_manager.return_operator_control(
            intervention_id,
            operator_id=registration.operator_id,
        )
        return self._transition_response(result)

    async def stop(self, intervention_id: str) -> OperatorTransitionResponse:
        self._registration(intervention_id)
        result = await self._intervention_manager.stop_intervention(intervention_id)
        return self._transition_response(result)

    def _registration(self, intervention_id: str) -> _Registration:
        try:
            return self._registrations[intervention_id]
        except KeyError as error:
            raise OperatorConsoleError(
                "INTERVENTION_NOT_FOUND",
                "Intervention was not found.",
                404,
            ) from error

    @staticmethod
    def _require_operator_control(state: SessionState, operator_id: str) -> None:
        if state.control_state == "terminal":
            raise OperatorConsoleError("SESSION_STOPPED", "Session has stopped.", 409)
        owner = state.owner
        if state.control_state != "operator_controlled" or not isinstance(owner, OperatorOwner):
            raise OperatorConsoleError(
                "INVALID_STATE",
                "Control is not currently owned by an operator.",
                409,
            )
        if owner.operator_id != operator_id:
            raise OperatorConsoleError(
                "NOT_OPERATOR_OWNER",
                "Control is owned by another operator.",
                409,
            )

    @staticmethod
    def _transition_response(result: InterventionResult) -> OperatorTransitionResponse:
        state = result.session_state
        return OperatorTransitionResponse(
            outcome=result.outcome,
            reason_code=result.reason_code,
            summary=result.summary,
            control_state=state.control_state if state is not None else None,
            state_label=(
                OperatorConsoleService._state_label(state.control_state)
                if state is not None
                else None
            ),
        )

    @staticmethod
    def _state_label(state: str) -> str:
        return {
            "automation_controlled": "Automation in control",
            "pause_requested": "Waiting for operator",
            "operator_controlled": "Operator in control",
            "resume_requested": "Resume validation required",
            "terminal": "Session stopped",
        }[state]
