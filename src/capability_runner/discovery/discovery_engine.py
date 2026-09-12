"""Bounded goal-driven discovery over semantic observations and trusted actions."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Protocol

from pydantic import SecretStr, TypeAdapter, ValidationError

from capability_runner.contracts.actions import ClickAction, FillAction
from capability_runner.contracts.browser_discovery import BrowserDiscoveryResult
from capability_runner.contracts.discovery import (
    ActDecision,
    CompleteDecision,
    DiscoveryDecision,
    DiscoveryFillAction,
    DiscoveryResult,
    DiscoveryTraceEntry,
    FailDecision,
    GoalSpanValueSource,
    RequestInterventionDecision,
    VerifiedCompletionEvidence,
)
from capability_runner.contracts.evaluation import EvaluationSnapshot
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import GatewayActionRequest, GatewayExecutionContext
from capability_runner.contracts.requests import DiscoveryRequest
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    SemanticTargetRef,
    SurfaceSessionRef,
)
from capability_runner.discovery.browser_discovery import BrowserDiscovery
from capability_runner.discovery.model_client import ModelClient, ModelClientError
from capability_runner.discovery.observation_presenter import ObservationPresenter
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.surfaces.surface_adapter import BrowserObservationPort

MAX_TURNS = 12
MAX_ACTIONS = 8
MAX_INVALID_RESPONSES = 2
UNCERTAIN_EFFECT_REASON = "ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED"

_DECISION_ADAPTER: TypeAdapter[DiscoveryDecision] = TypeAdapter(DiscoveryDecision)


class SemanticSnapshotCollector(Protocol):
    async def collect(
        self,
        session: SurfaceSessionRef,
        profile: ApplicationProfile,
        targets: tuple[SemanticTargetRef, ...],
    ) -> EvaluationSnapshot: ...


class EvidenceWriter(Protocol):
    def record(self, event: EvidenceEvent) -> object: ...


class DiscoveryEngine:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        action_gateway: ActionGateway,
        snapshot_collector: SemanticSnapshotCollector,
        observation_presenter: ObservationPresenter | None = None,
        evidence_recorder: EvidenceWriter | None = None,
    ) -> None:
        self._model_client = model_client
        self._action_gateway = action_gateway
        self._snapshot_collector = snapshot_collector
        self._presenter = observation_presenter or ObservationPresenter()
        self._evidence_recorder = evidence_recorder

    async def discover_unprofiled(
        self,
        request: DiscoveryRequest,
        context: GatewayExecutionContext,
        surface: BrowserObservationPort,
    ) -> BrowserDiscoveryResult:
        def event(code: str, metadata: dict[str, object]) -> None:
            self._record_event(context, reason_code=code, outcome="observed", metadata=metadata)

        event("DISCOVERY_STARTED", {"mode": "profile_less"})
        result = await BrowserDiscovery(
            self._model_client, self._action_gateway, surface, event
        ).discover(request, context)
        event(
            "DISCOVERY_COMPLETED",
            {
                "result_reason_code": result.result.reason_code,
                "turn_count": result.result.turns,
                "action_count": result.result.actions,
            },
        )
        return result

    async def discover(
        self,
        request: DiscoveryRequest,
        context: GatewayExecutionContext,
    ) -> DiscoveryResult:
        self._record_event(
            context,
            reason_code="DISCOVERY_STARTED",
            outcome="started",
            metadata={
                "max_steps": request.max_steps,
                "required_completion_target_count": len(request.required_completion_targets),
                "timeout_seconds": request.timeout_seconds,
            },
        )
        try:
            async with asyncio.timeout(request.timeout_seconds):
                result = await self._discover_bounded(request, context)
        except TimeoutError:
            result = self._result("FAILED", "DISCOVERY_TIMEOUT", 0, 0, ())
        self._record_event(
            context,
            reason_code="DISCOVERY_COMPLETED",
            outcome=result.outcome.casefold(),
            metadata={
                "action_count": result.actions,
                "result_reason_code": result.reason_code,
                "turn_count": result.turns,
                "verified_target_count": len(result.verified_targets),
            },
        )
        return result

    async def _discover_bounded(
        self,
        request: DiscoveryRequest,
        context: GatewayExecutionContext,
    ) -> DiscoveryResult:
        target_refs = tuple(
            sorted(
                (binding.semantic_target for binding in context.profile.target_bindings),
                key=lambda item: item.value,
            )
        )
        trusted_targets = {item.value for item in target_refs}
        required_completion_targets = {item.value for item in request.required_completion_targets}
        if not required_completion_targets <= trusted_targets:
            return self._result(
                "FAILED",
                "REQUIRED_COMPLETION_TARGET_UNKNOWN",
                0,
                0,
                (),
            )
        trace: list[DiscoveryTraceEntry] = []
        actions = 0
        invalid_responses = 0
        repair_code: str | None = None
        previous_proposal: tuple[str, str, str | None] | None = None
        previous_snapshot: tuple[tuple[str, str, str | None], ...] | None = None
        executed_goal_values: dict[str, tuple[str, GoalSpanValueSource]] = {}
        max_turns = min(request.max_steps, MAX_TURNS)

        for turn in range(1, max_turns + 1):
            try:
                snapshot = await self._snapshot_collector.collect(
                    context.surface_session,
                    context.profile,
                    target_refs,
                )
            except Exception:
                return self._result("FAILED", "OBSERVATION_FAILED", turn - 1, actions, tuple(trace))

            observation_fingerprint = _snapshot_fingerprint(snapshot)
            self._record_event(
                context,
                reason_code="DISCOVERY_OBSERVATION_COLLECTED",
                outcome="collected",
                metadata={
                    "observation_fingerprint": observation_fingerprint,
                    "observed_target_count": len(snapshot.observed_targets),
                    "turn": turn,
                    "visible_target_count": sum(
                        item.state == "VISIBLE" for item in snapshot.observed_targets
                    ),
                },
            )

            model_request = self._presenter.present(
                goal=request.goal,
                profile=context.profile,
                snapshot=snapshot,
                turn=turn,
                trace=tuple(trace),
                repair_code=repair_code,
                required_completion_targets=request.required_completion_targets,
            )
            try:
                response = await self._model_client.complete(model_request)
            except ModelClientError as error:
                return self._result(
                    "FAILED",
                    f"MODEL_{error.code}",
                    turn,
                    actions,
                    tuple(trace),
                )

            try:
                decision = _parse_decision(response.content)
            except (json.JSONDecodeError, ValidationError, ValueError):
                invalid_responses += 1
                trace.append(
                    DiscoveryTraceEntry(
                        turn=turn,
                        decision_kind="INVALID",
                        observation_fingerprint=_snapshot_fingerprint(snapshot),
                        outcome="INVALID_MODEL_RESPONSE",
                    )
                )
                if invalid_responses >= MAX_INVALID_RESPONSES:
                    return self._result(
                        "FAILED", "MODEL_INVALID_RESPONSE", turn, actions, tuple(trace)
                    )
                repair_code = "INVALID_MODEL_RESPONSE"
                continue

            action = decision.action if isinstance(decision, ActDecision) else None
            self._record_event(
                context,
                reason_code="DISCOVERY_DECISION_RECEIVED",
                outcome="received",
                step_id=f"discovery-step-{actions + 1}" if action is not None else None,
                metadata={
                    "action_kind": action.kind if action is not None else None,
                    "decision_kind": decision.kind,
                    "observation_fingerprint": observation_fingerprint,
                    "semantic_target": action.target if action is not None else None,
                    "turn": turn,
                },
            )

            if isinstance(decision, CompleteDecision):
                completion_evidence = _verified_completion_evidence(
                    decision,
                    snapshot,
                    request.goal,
                    trusted_targets,
                    executed_goal_values,
                )
                completion_failure = "COMPLETION_NOT_GROUNDED"
                if completion_evidence is not None and not required_completion_targets <= {
                    item.target for item in completion_evidence
                }:
                    completion_evidence = None
                    completion_failure = "COMPLETION_EVIDENCE_MISSING"
                if completion_evidence is None:
                    invalid_responses += 1
                    trace.append(
                        DiscoveryTraceEntry(
                            turn=turn,
                            decision_kind="INVALID",
                            observation_fingerprint=_snapshot_fingerprint(snapshot),
                            outcome=completion_failure,
                        )
                    )
                    if invalid_responses >= MAX_INVALID_RESPONSES:
                        return self._result(
                            "FAILED", completion_failure, turn, actions, tuple(trace)
                        )
                    repair_code = completion_failure
                    continue
                verified_targets = tuple(item.target for item in completion_evidence)
                trace.append(
                    DiscoveryTraceEntry(
                        turn=turn,
                        decision_kind="COMPLETE",
                        observation_fingerprint=_snapshot_fingerprint(snapshot),
                        outcome="VERIFIED",
                    )
                )
                return self._result(
                    "SUCCESS",
                    "COMPLETED",
                    turn,
                    actions,
                    tuple(trace),
                    verified_targets=verified_targets,
                    completion_evidence=completion_evidence,
                )

            if isinstance(decision, RequestInterventionDecision):
                trace.append(
                    DiscoveryTraceEntry(
                        turn=turn,
                        decision_kind="REQUEST_INTERVENTION",
                        observation_fingerprint=_snapshot_fingerprint(snapshot),
                        outcome="INTERVENTION_REQUESTED",
                    )
                )
                return self._result(
                    "INTERVENTION_REQUIRED",
                    decision.reason_code,
                    turn,
                    actions,
                    tuple(trace),
                )

            if isinstance(decision, FailDecision):
                trace.append(
                    DiscoveryTraceEntry(
                        turn=turn,
                        decision_kind="FAIL",
                        observation_fingerprint=_snapshot_fingerprint(snapshot),
                        outcome="MODEL_DECLARED_FAILURE",
                    )
                )
                return self._result("FAILED", decision.reason_code, turn, actions, tuple(trace))

            validation_code = _validate_action(decision, request.goal, trusted_targets)
            if validation_code is not None:
                invalid_responses += 1
                trace.append(
                    DiscoveryTraceEntry(
                        turn=turn,
                        decision_kind="INVALID",
                        observation_fingerprint=_snapshot_fingerprint(snapshot),
                        outcome=validation_code,
                    )
                )
                if invalid_responses >= MAX_INVALID_RESPONSES:
                    return self._result("FAILED", validation_code, turn, actions, tuple(trace))
                repair_code = validation_code
                continue

            if actions >= MAX_ACTIONS:
                return self._result("FAILED", "ACTION_LIMIT_REACHED", turn, actions, tuple(trace))

            snapshot_key = _snapshot_key(snapshot)
            proposal_key = _proposal_key(decision)
            if proposal_key == previous_proposal and snapshot_key == previous_snapshot:
                return self._result("FAILED", "NO_PROGRESS", turn, actions, tuple(trace))

            gateway_result = await self._action_gateway.execute(
                _gateway_request(decision, request, turn, actions + 1),
                context,
            )
            actions += 1
            value_source = _goal_span_source(decision, request.goal)
            trace.append(
                DiscoveryTraceEntry(
                    turn=turn,
                    decision_kind="ACT",
                    action_kind=decision.action.kind,
                    semantic_target=decision.action.target,
                    value_source=value_source,
                    gateway_outcome=gateway_result.outcome,
                    observation_fingerprint=_snapshot_fingerprint(snapshot),
                    outcome=gateway_result.reason_code,
                )
            )
            if (
                gateway_result.outcome == "EXECUTED"
                and isinstance(decision.action, DiscoveryFillAction)
                and value_source is not None
            ):
                executed_goal_values[decision.action.target] = (
                    decision.action.value.get_secret_value(),
                    value_source,
                )
            previous_proposal = proposal_key
            previous_snapshot = snapshot_key
            repair_code = None

            if gateway_result.outcome == "DENIED":
                return self._result("FAILED", "POLICY_DENIED", turn, actions, tuple(trace))
            if gateway_result.outcome == "APPROVAL_REQUIRED":
                return self._result(
                    "INTERVENTION_REQUIRED",
                    "APPROVAL_REQUIRED",
                    turn,
                    actions,
                    tuple(trace),
                )
            if gateway_result.outcome == "FAILED":
                if gateway_result.reason_code == UNCERTAIN_EFFECT_REASON:
                    return self._result(
                        "INTERVENTION_REQUIRED",
                        "ACTION_EFFECT_UNCERTAIN",
                        turn,
                        actions,
                        tuple(trace),
                    )
                return self._result("FAILED", "ACTION_FAILED", turn, actions, tuple(trace))

        return self._result("FAILED", "TURN_LIMIT_REACHED", max_turns, actions, tuple(trace))

    def _record_event(
        self,
        context: GatewayExecutionContext,
        *,
        reason_code: str,
        outcome: str,
        metadata: dict[str, object],
        step_id: str | None = None,
    ) -> None:
        if self._evidence_recorder is None:
            return
        self._evidence_recorder.record(
            EvidenceEvent(
                event_type="lifecycle",
                component="discovery-engine",
                run_id=context.run_id,
                session_id=context.control_session_id,
                step_id=step_id,
                outcome=outcome,
                reason_code=reason_code,
                metadata=metadata,
            )
        )

    @staticmethod
    def _result(
        outcome: str,
        reason_code: str,
        turns: int,
        actions: int,
        trace: tuple[DiscoveryTraceEntry, ...],
        *,
        verified_targets: tuple[str, ...] = (),
        completion_evidence: tuple[VerifiedCompletionEvidence, ...] = (),
    ) -> DiscoveryResult:
        return DiscoveryResult.model_validate(
            {
                "outcome": outcome,
                "reason_code": reason_code,
                "turns": turns,
                "actions": actions,
                "verified_targets": verified_targets,
                "completion_evidence": completion_evidence,
                "trace": trace,
            }
        )


def _parse_decision(content: str) -> DiscoveryDecision:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) < 3 or lines[-1].strip() != "```":
            raise ValueError("invalid fenced JSON response")
        if lines[0].strip() not in {"```", "```json", "```JSON"}:
            raise ValueError("unsupported fenced response")
        if any("```" in line for line in lines[1:-1]):
            raise ValueError("multiple fenced objects are not allowed")
        stripped = "\n".join(lines[1:-1]).strip()
    return _DECISION_ADAPTER.validate_python(json.loads(stripped))


def _validate_action(
    decision: ActDecision,
    goal: str,
    trusted_targets: set[str],
) -> str | None:
    if decision.action.target not in trusted_targets:
        return "UNKNOWN_TARGET"
    if isinstance(decision.action, DiscoveryFillAction):
        value = decision.action.value.get_secret_value()
        if not value or value not in goal:
            return "UNGROUNDED_FILL_VALUE"
    return None


def _verified_completion_evidence(
    decision: CompleteDecision,
    snapshot: EvaluationSnapshot,
    goal: str,
    trusted_targets: set[str],
    executed_goal_values: dict[str, tuple[str, GoalSpanValueSource]],
) -> tuple[VerifiedCompletionEvidence, ...] | None:
    current = {
        item.target.value: item.text
        for item in snapshot.observed_targets
        if item.state == "VISIBLE" and item.text is not None
    }
    evidence_targets: set[str] = set()
    goal_grounded = False
    verified: list[VerifiedCompletionEvidence] = []
    for evidence in decision.evidence:
        observed_text = evidence.observed_text.get_secret_value()
        if evidence.target not in trusted_targets or evidence.target in evidence_targets:
            return None
        if current.get(evidence.target) != observed_text:
            return None
        evidence_targets.add(evidence.target)
        if observed_text and observed_text in goal:
            goal_grounded = True
        matching_source = next(
            (
                source_target
                for source_target, (value, _) in executed_goal_values.items()
                if value == observed_text
            ),
            None,
        )
        verified.append(
            VerifiedCompletionEvidence(
                target=evidence.target,
                text_fingerprint=_text_fingerprint(observed_text),
                goal_span_action_target=matching_source,
            )
        )
    return tuple(verified) if goal_grounded else None


def _gateway_request(
    decision: ActDecision,
    request: DiscoveryRequest,
    turn: int,
    action_number: int,
) -> GatewayActionRequest:
    target = SemanticTargetRef(value=decision.action.target)
    if isinstance(decision.action, DiscoveryFillAction):
        action = FillAction(
            target=request.target,
            value=SecretStr(decision.action.value.get_secret_value()),
        )
    else:
        action = ClickAction(target=request.target)
    return GatewayActionRequest(
        action_id=f"discovery-{action_number}",
        step_id=f"discovery-turn-{turn}",
        semantic_target=target,
        action=action,
    )


def _snapshot_key(snapshot: EvaluationSnapshot) -> tuple[tuple[str, str, str | None], ...]:
    return tuple(
        sorted(
            (
                item.target.value,
                item.state,
                item.text,
            )
            for item in snapshot.observed_targets
        )
    )


def _proposal_key(decision: ActDecision) -> tuple[str, str, str | None]:
    value = (
        decision.action.value.get_secret_value()
        if isinstance(decision.action, DiscoveryFillAction)
        else None
    )
    return decision.action.kind, decision.action.target, value


def _goal_span_source(
    decision: ActDecision,
    goal: str,
) -> GoalSpanValueSource | None:
    if not isinstance(decision.action, DiscoveryFillAction):
        return None
    value = decision.action.value.get_secret_value()
    start = goal.find(value)
    if start < 0:
        return None
    return GoalSpanValueSource(start=start, end=start + len(value))


def _snapshot_fingerprint(snapshot: EvaluationSnapshot) -> str:
    structural_state = [
        (item.target.value, item.state)
        for item in sorted(snapshot.observed_targets, key=lambda item: item.target.value)
    ]
    payload = json.dumps(structural_state, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _text_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
