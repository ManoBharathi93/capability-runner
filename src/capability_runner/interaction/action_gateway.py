"""Controlled dispatch path for automated surface actions."""

from __future__ import annotations

from typing import Protocol

from capability_runner.contracts.actions import FillAction
from capability_runner.contracts.browser_discovery import BrowserScope
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayOutcome,
    GatewayResult,
)
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyContext,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.sessions import SessionControllerError
from capability_runner.contracts.surfaces import (
    BrowserTargetBinding,
    SurfaceActionOutcome,
    SurfaceActionResult,
)
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interaction.policy_guard import PolicyGuard, observed_action_allowed
from capability_runner.interaction.session_controller import SessionController
from capability_runner.surfaces.surface_adapter import BrowserObservationPort, SurfaceAdapter


class EvidenceWriter(Protocol):
    def record(
        self,
        event: EvidenceEvent,
        *,
        redaction_context: RedactionContext | None = None,
    ) -> object: ...


class ActionGateway:
    """Authorize, serialize, execute, and record one automated surface action."""

    def __init__(
        self,
        *,
        policy_guard: PolicyGuard,
        session_controller: SessionController,
        surface_adapter: SurfaceAdapter,
        evidence_recorder: EvidenceWriter,
        observation_adapter: BrowserObservationPort | None = None,
        browser_scope: BrowserScope | None = None,
    ) -> None:
        self._policy_guard = policy_guard
        self._session_controller = session_controller
        self._surface_adapter = surface_adapter
        self._evidence_recorder = evidence_recorder
        self._observation_adapter = observation_adapter
        self._browser_scope = browser_scope

    async def execute_observed(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        *,
        observation_id: str,
        element_ref: str,
    ) -> GatewayResult:
        if self._observation_adapter is None or self._browser_scope is None:
            return self._result(request, "DENIED", "POLICY_DENIED", "No browser scope authorized.")
        try:
            element = await self._observation_adapter.resolve_observed(
                context.surface_session,
                observation_id,
                element_ref,
            )
        except Exception as error:
            code = (
                str(error)
                if str(error) in {"STALE_ELEMENT_REF", "UNKNOWN_ELEMENT_REF", "TARGET_AMBIGUOUS"}
                else "STALE_ELEMENT_REF"
            )
            result = self._result(
                request,
                "FAILED",
                code,
                "Current element reference could not be validated.",
            )
            return self._record_before_dispatch(result, request, context)
        allowed = (
            observed_action_allowed(element, self._browser_scope)
            and request.action.kind == element.action_kind
        )
        if element.binding is None:
            return self._result(request, "FAILED", "TARGET_BINDING_NOT_FOUND", "No binding.")
        binding = element.binding.model_copy(update={"semantic_target": request.semantic_target})
        profile = context.profile.model_copy(update={"target_bindings": (binding,)})
        rule_type = FillPolicyRule if isinstance(request.action, FillAction) else ClickPolicyRule
        guard = PolicyGuard(
            PolicyDefinition(
                policy_id="observed-read-only",
                version="1",
                allowed_contexts=(
                    TrustedApplicationProfile(
                        application=profile.application_family, profile=profile.variant
                    ),
                ),
                rules=(
                    rule_type(
                        rule_id="operator-route-scope",
                        effect="ALLOW" if allowed else "DENY",
                        semantic_target=request.semantic_target,
                    ),
                ),
            )
        )
        gateway = ActionGateway(
            policy_guard=guard,
            session_controller=self._session_controller,
            surface_adapter=self._surface_adapter,
            evidence_recorder=self._evidence_recorder,
        )
        return await gateway.execute(request, context.model_copy(update={"profile": profile}))

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        binding = self._find_binding(context, request)
        if binding is None:
            result = self._result(
                request,
                "FAILED",
                "TARGET_BINDING_NOT_FOUND",
                "Trusted target binding is not configured.",
            )
            return self._record_before_dispatch(result, request, context)

        if self._browser_scope is not None and self._observation_adapter is not None:
            try:
                element = await self._observation_adapter.inspect_bound_element(
                    context.surface_session,
                    binding,
                )
                allowed = observed_action_allowed(element, self._browser_scope)
                if allowed and element.binding is not None:
                    binding = element.binding.model_copy(
                        update={"semantic_target": request.semantic_target}
                    )
            except Exception:
                allowed = False
            if not allowed:
                result = self._result(
                    request,
                    "DENIED",
                    "POLICY_DENIED",
                    "Current browser action is outside the read-only scope.",
                )
                return self._record_before_dispatch(result, request, context)

        decision = self._policy_guard.evaluate(
            request.action,
            PolicyContext(
                application=context.profile.application_family,
                profile=context.profile.variant,
            ),
            request.semantic_target,
        )
        decision_result = self._record_policy_decision(
            request, context, decision.decision, decision.reason_code, decision.rule_id
        )
        if decision_result is not None:
            return decision_result
        if decision.decision == "DENY":
            return self._result(request, "DENIED", decision.reason_code, decision.summary)
        if decision.decision == "REQUIRE_APPROVAL":
            return self._result(
                request, "APPROVAL_REQUIRED", decision.reason_code, decision.summary
            )

        try:
            async with self._session_controller.automation_dispatch(
                context.control_session_id,
                context.expected_generation,
            ):
                surface_result = await self._surface_adapter.perform_action(
                    context.surface_session,
                    request.action,
                    binding,
                )
        except SessionControllerError as error:
            result = self._result(request, "FAILED", error.code, error.summary)
            return self._record_before_dispatch(result, request, context)
        except Exception:
            result = self._result(
                request,
                "FAILED",
                "SURFACE_ADAPTER_ERROR",
                "Surface adapter raised an infrastructure error.",
            )
            return self._record_after_dispatch(result, request, context)

        result = self._surface_result(request, surface_result)
        return self._record_after_dispatch(result, request, context)

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

    def _record_policy_decision(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        decision: str,
        reason_code: str,
        rule_id: str | None,
    ) -> GatewayResult | None:
        try:
            self._evidence_recorder.record(
                EvidenceEvent(
                    event_type="policy",
                    component="action-gateway",
                    run_id=context.run_id,
                    session_id=context.control_session_id,
                    step_id=request.step_id,
                    action_id=request.action_id,
                    outcome=decision.casefold(),
                    reason_code=reason_code,
                    metadata={
                        "semantic_target": request.semantic_target.value,
                        "action_kind": request.action.kind,
                        "rule_id": rule_id,
                    },
                ),
                redaction_context=self._redaction_context(request),
            )
        except Exception:
            return self._result(
                request,
                "FAILED",
                "EVIDENCE_PRE_ACTION_FAILED",
                "Required policy evidence could not be recorded.",
            )
        return None

    def _record_before_dispatch(
        self,
        result: GatewayResult,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        try:
            self._record_action_event(result, request, context)
        except Exception:
            return self._result(
                request,
                "FAILED",
                "EVIDENCE_PRE_ACTION_FAILED",
                "Required pre-action evidence could not be recorded.",
            )
        return result

    def _record_after_dispatch(
        self,
        result: GatewayResult,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        try:
            self._record_action_event(result, request, context)
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
                "Surface dispatch completed but action evidence could not be recorded.",
                surface_outcome=result.surface_outcome,
            )
        return result

    def _record_action_event(
        self,
        result: GatewayResult,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> None:
        self._evidence_recorder.record(
            EvidenceEvent(
                event_type="action",
                component="action-gateway",
                run_id=context.run_id,
                session_id=context.control_session_id,
                step_id=request.step_id,
                action_id=request.action_id,
                outcome=result.outcome.casefold(),
                reason_code=result.reason_code,
                metadata={
                    "semantic_target": request.semantic_target.value,
                    "action_kind": request.action.kind,
                    "surface_outcome": result.surface_outcome,
                },
            ),
            redaction_context=self._redaction_context(request),
        )

    @staticmethod
    def _surface_result(
        request: GatewayActionRequest,
        surface_result: SurfaceActionResult,
    ) -> GatewayResult:
        if surface_result.outcome == "APPLIED":
            return ActionGateway._result(
                request,
                "EXECUTED",
                "APPLIED",
                surface_result.summary,
                surface_outcome=surface_result.outcome,
            )
        return ActionGateway._result(
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
