"""Policy-checked dispatch path for explicit operator actions."""

from __future__ import annotations

from typing import Protocol

from capability_runner.contracts.actions import FillAction
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayOutcome,
    GatewayResult,
)
from capability_runner.contracts.policy import PolicyContext
from capability_runner.contracts.sessions import SessionControllerError
from capability_runner.contracts.surfaces import (
    BrowserTargetBinding,
    SurfaceActionOutcome,
    SurfaceActionResult,
)
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.surfaces.surface_adapter import SurfaceAdapter


class EvidenceWriter(Protocol):
    def record(
        self,
        event: EvidenceEvent,
        *,
        redaction_context: RedactionContext | None = None,
    ) -> object: ...


class OperatorActionGateway:
    def __init__(
        self,
        *,
        policy_guard: PolicyGuard,
        session_controller: SessionController,
        surface_adapter: SurfaceAdapter,
        evidence_recorder: EvidenceWriter,
    ) -> None:
        self._policy_guard = policy_guard
        self._session_controller = session_controller
        self._surface_adapter = surface_adapter
        self._evidence_recorder = evidence_recorder

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        *,
        operator_id: str,
    ) -> GatewayResult:
        binding = self._find_binding(context, request)
        if binding is None:
            return self._record_result(
                self._result(
                    request,
                    "FAILED",
                    "TARGET_BINDING_NOT_FOUND",
                    "Trusted target binding is not configured.",
                ),
                request,
                context,
            )

        decision = self._policy_guard.evaluate(
            request.action,
            PolicyContext(
                application=context.profile.application_family,
                profile=context.profile.variant,
            ),
            request.semantic_target,
        )
        try:
            self._record_policy(request, context, decision.decision, decision.reason_code)
        except Exception:
            return self._result(
                request,
                "FAILED",
                "EVIDENCE_PRE_ACTION_FAILED",
                "Required operator policy evidence could not be recorded.",
            )
        if decision.decision == "DENY":
            return self._record_result(
                self._result(request, "DENIED", decision.reason_code, decision.summary),
                request,
                context,
            )
        if decision.decision == "REQUIRE_APPROVAL":
            return self._record_result(
                self._result(
                    request,
                    "APPROVAL_REQUIRED",
                    decision.reason_code,
                    decision.summary,
                ),
                request,
                context,
            )

        try:
            async with self._session_controller.operator_dispatch(
                context.control_session_id,
                context.expected_generation,
                operator_id,
            ):
                surface_result = await self._surface_adapter.perform_action(
                    context.surface_session,
                    request.action,
                    binding,
                )
        except SessionControllerError as error:
            result = self._result(request, "FAILED", error.code, error.summary)
            return self._record_result(result, request, context)
        except Exception:
            result = self._result(
                request,
                "FAILED",
                "SURFACE_ADAPTER_ERROR",
                "Surface adapter raised an infrastructure error.",
            )
            return self._record_result(result, request, context)

        result = self._surface_result(request, surface_result)
        return self._record_result(result, request, context)

    @staticmethod
    def _find_binding(
        context: GatewayExecutionContext,
        request: GatewayActionRequest,
    ) -> BrowserTargetBinding | None:
        return next(
            (
                binding
                for binding in context.profile.target_bindings
                if binding.semantic_target == request.semantic_target
            ),
            None,
        )

    def _record_policy(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        decision: str,
        reason_code: str,
    ) -> None:
        self._evidence_recorder.record(
            EvidenceEvent(
                event_type="policy",
                component="operator-action-gateway",
                run_id=context.run_id,
                session_id=context.control_session_id,
                step_id=request.step_id,
                action_id=request.action_id,
                outcome=decision.casefold(),
                reason_code=reason_code,
                metadata={
                    "semantic_target": request.semantic_target.value,
                    "action_kind": request.action.kind,
                },
            ),
            redaction_context=self._redaction_context(request),
        )

    def _record_result(
        self,
        result: GatewayResult,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        try:
            self._evidence_recorder.record(
                EvidenceEvent(
                    event_type="intervention",
                    component="operator-action-gateway",
                    run_id=context.run_id,
                    session_id=context.control_session_id,
                    step_id=request.step_id,
                    action_id=request.action_id,
                    outcome=result.outcome.casefold(),
                    reason_code="OPERATOR_ACTION",
                    summary=result.summary,
                    metadata={
                        "semantic_target": request.semantic_target.value,
                        "action_kind": request.action.kind,
                        "result_reason_code": result.reason_code,
                        "surface_outcome": result.surface_outcome,
                    },
                ),
                redaction_context=self._redaction_context(request),
            )
        except Exception:
            reason_code = (
                "ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED"
                if result.outcome == "EXECUTED"
                else "POST_ACTION_EVIDENCE_FAILED"
            )
            return self._result(
                request,
                "FAILED",
                reason_code,
                "Operator dispatch completed but action evidence could not be recorded.",
                surface_outcome=result.surface_outcome,
            )
        return result

    @staticmethod
    def _surface_result(
        request: GatewayActionRequest,
        surface_result: SurfaceActionResult,
    ) -> GatewayResult:
        if surface_result.outcome == "APPLIED":
            return OperatorActionGateway._result(
                request,
                "EXECUTED",
                "APPLIED",
                surface_result.summary,
                surface_outcome=surface_result.outcome,
            )
        return OperatorActionGateway._result(
            request,
            "FAILED",
            surface_result.outcome,
            surface_result.summary,
            surface_outcome=surface_result.outcome,
        )

    @staticmethod
    def _redaction_context(request: GatewayActionRequest) -> RedactionContext:
        if isinstance(request.action, FillAction):
            return RedactionContext(
                explicit_values=frozenset({request.action.value.get_secret_value()})
            )
        return RedactionContext()

    @staticmethod
    def _result(
        request: GatewayActionRequest,
        outcome: GatewayOutcome,
        reason_code: str,
        summary: str,
        *,
        surface_outcome: SurfaceActionOutcome | None = None,
    ) -> GatewayResult:
        return GatewayResult(
            outcome=outcome,
            reason_code=reason_code,
            summary=summary,
            action_id=request.action_id,
            semantic_target=request.semantic_target,
            surface_outcome=surface_outcome,
        )
