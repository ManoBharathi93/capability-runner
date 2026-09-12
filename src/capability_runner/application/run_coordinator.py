"""Application orchestration for approval-blocked Replay continuation."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from pydantic import SecretStr

from capability_runner.capabilities.capability_validator import ValidatedCapability
from capability_runner.contracts.continuation import ReplayContinuationResult
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import GatewayExecutionContext
from capability_runner.contracts.intervention import (
    InterventionRecord,
    InterventionRequest,
    InterventionResult,
    ResumeValidationResult,
)
from capability_runner.contracts.replay import ReplayCheckpoint, ReplayResult


class ReplayContinuationEngine(Protocol):
    async def validate_resume(
        self,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ResumeValidationResult: ...

    async def resume(
        self,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ReplayResult: ...


class ContinuationInterventionManager(Protocol):
    async def request_intervention(self, request: InterventionRequest) -> InterventionResult: ...

    async def complete_resume_validation(self, intervention_id: str) -> InterventionResult: ...


class EvidenceWriter(Protocol):
    def record(self, event: EvidenceEvent) -> object: ...


@dataclass(slots=True)
class _PendingReplayContinuation:
    capability: ValidatedCapability = field(repr=False)
    checkpoint: ReplayCheckpoint
    runtime_inputs: tuple[tuple[str, SecretStr], ...] = field(repr=False)
    context: GatewayExecutionContext = field(repr=False)
    resume_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def revealed_inputs(self) -> dict[str, str]:
        return {name: value.get_secret_value() for name, value in self.runtime_inputs}


class ReplayContinuationRegistry:
    """Process-local continuation state shared with the P4.1 validator."""

    def __init__(self) -> None:
        self._pending: dict[str, _PendingReplayContinuation] = {}
        self._consumed: set[str] = set()

    def register(
        self,
        intervention_id: str,
        *,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> _PendingReplayContinuation:
        if intervention_id in self._pending or intervention_id in self._consumed:
            raise ValueError("continuation identifier already exists")
        pending = _PendingReplayContinuation(
            capability=capability,
            checkpoint=checkpoint,
            runtime_inputs=tuple(
                (name, SecretStr(value)) for name, value in sorted(runtime_inputs.items())
            ),
            context=context,
        )
        self._pending[intervention_id] = pending
        return pending

    def get(self, intervention_id: str) -> _PendingReplayContinuation | None:
        return self._pending.get(intervention_id)

    def discard(self, intervention_id: str) -> None:
        self._pending.pop(intervention_id, None)

    def consume(
        self,
        intervention_id: str,
        pending: _PendingReplayContinuation,
    ) -> bool:
        if self._pending.get(intervention_id) is not pending:
            return False
        del self._pending[intervention_id]
        self._consumed.add(intervention_id)
        return True

    def was_consumed(self, intervention_id: str) -> bool:
        return intervention_id in self._consumed


class ReplayContinuationResumeValidator:
    """Adapt fresh Replay state assessment to P4.1's validation protocol."""

    def __init__(
        self,
        *,
        registry: ReplayContinuationRegistry,
        replay_engine: ReplayContinuationEngine,
    ) -> None:
        self._registry = registry
        self._replay_engine = replay_engine

    async def validate(self, record: InterventionRecord) -> ResumeValidationResult:
        pending = self._registry.get(record.intervention_id)
        if pending is None or not self._matches_record(pending, record):
            return ResumeValidationResult(
                outcome="INVALID",
                reason_code="INVALID_CONTINUATION",
                summary="Replay continuation does not match the intervention.",
            )
        return await self._replay_engine.validate_resume(
            pending.capability,
            pending.checkpoint,
            pending.revealed_inputs(),
            pending.context,
        )

    @staticmethod
    def _matches_record(
        pending: _PendingReplayContinuation,
        record: InterventionRecord,
    ) -> bool:
        return (
            record.run_id == pending.context.run_id
            and record.control_session_id == pending.context.control_session_id
            and record.surface_session == pending.context.surface_session
            and record.requested_generation > pending.checkpoint.suspended_generation
        )


class ReplayContinuationCoordinator:
    """Suspend and resume one Replay invocation without performing surface actions."""

    def __init__(
        self,
        *,
        registry: ReplayContinuationRegistry,
        intervention_manager: ContinuationInterventionManager,
        replay_engine: ReplayContinuationEngine,
        evidence_recorder: EvidenceWriter | None = None,
    ) -> None:
        self._registry = registry
        self._intervention_manager = intervention_manager
        self._replay_engine = replay_engine
        self._evidence_recorder = evidence_recorder

    async def suspend_for_intervention(
        self,
        *,
        intervention_id: str,
        replay_result: ReplayResult,
        capability: ValidatedCapability,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ReplayContinuationResult:
        checkpoint = replay_result.checkpoint
        if (
            replay_result.outcome != "FAILURE"
            or replay_result.reason_code != "APPROVAL_REQUIRED"
            or checkpoint is None
            or replay_result.run_id != context.run_id
            or checkpoint.suspended_generation != context.expected_generation
            or checkpoint.capability_id != capability.definition.capability_id
            or checkpoint.capability_version != capability.definition.capability_version
            or checkpoint.blocked_step_index >= len(capability.definition.steps)
            or capability.definition.steps[checkpoint.blocked_step_index].step_id
            != checkpoint.blocked_step_id
        ):
            return self._result(
                "INVALID_CONTINUATION",
                "UNSAFE_REPLAY_SUSPENSION",
                "Replay result is not safely resumable.",
                replay_result=replay_result,
            )
        try:
            self._registry.register(
                intervention_id,
                capability=capability,
                checkpoint=checkpoint,
                runtime_inputs=runtime_inputs,
                context=context,
            )
        except ValueError:
            return self._result(
                "INVALID_CONTINUATION",
                "CONTINUATION_ALREADY_EXISTS",
                "Replay continuation identifier already exists.",
                replay_result=replay_result,
            )

        intervention = await self._intervention_manager.request_intervention(
            InterventionRequest(
                intervention_id=intervention_id,
                run_id=context.run_id,
                control_session_id=context.control_session_id,
                surface_session=context.surface_session,
                reason_code="APPROVAL_REQUIRED",
                summary="Human approval/action is required before automation can continue.",
            )
        )
        if intervention.outcome != "INTERVENTION_REQUESTED" or intervention.record is None:
            self._registry.discard(intervention_id)
            return self._result(
                "FAILURE",
                intervention.reason_code,
                intervention.summary,
                replay_result=replay_result,
            )
        self._record_intervention_context(
            intervention_id=intervention_id,
            capability=capability,
            checkpoint=checkpoint,
            runtime_inputs=runtime_inputs,
            context=context,
            control_generation=intervention.record.requested_generation,
        )
        return self._result(
            "INTERVENTION_REQUIRED",
            "APPROVAL_REQUIRED",
            "Human approval/action is required before automation can continue.",
            intervention=intervention.record,
            replay_result=replay_result,
            generation_before=checkpoint.suspended_generation,
        )

    def _record_intervention_context(
        self,
        *,
        intervention_id: str,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
        control_generation: int,
    ) -> None:
        if self._evidence_recorder is None:
            return
        step = capability.definition.steps[checkpoint.blocked_step_index]
        self._evidence_recorder.record(
            EvidenceEvent(
                event_type="intervention",
                component="replay-continuation-coordinator",
                run_id=context.run_id,
                session_id=context.control_session_id,
                step_id=checkpoint.blocked_step_id,
                outcome="context_recorded",
                reason_code="INTERVENTION_CONTEXT_RECORDED",
                summary="Sanitized replay intervention context recorded.",
                metadata={
                    "action_effect_state": checkpoint.action_effect_state,
                    "action_kind": step.action.kind,
                    "blocked_step_index": checkpoint.blocked_step_index,
                    "capability_id": capability.definition.capability_id,
                    "capability_name": capability.definition.name,
                    "capability_version": capability.definition.capability_version,
                    "control_generation": control_generation,
                    "current_state": "blocked_before_dispatch",
                    "input_names": sorted(runtime_inputs),
                    "intervention_id": intervention_id,
                    "semantic_target": step.action.target.value,
                    "surface_session_id": context.surface_session.surface_session_id,
                },
            )
        )

    async def resume(self, intervention_id: str) -> ReplayContinuationResult:
        pending = self._registry.get(intervention_id)
        if pending is None:
            return self._unavailable(intervention_id)
        async with pending.resume_lock:
            if self._registry.get(intervention_id) is not pending:
                return self._unavailable(intervention_id)
            transition = await self._intervention_manager.complete_resume_validation(
                intervention_id
            )
            if transition.outcome != "RESUMED" or transition.session_state is None:
                if transition.outcome == "SESSION_STOPPED":
                    self._registry.consume(intervention_id, pending)
                return self._transition_failure(transition, pending.checkpoint)

            resumed_context = pending.context.model_copy(
                update={
                    "expected_generation": transition.session_state.control_generation,
                }
            )
            if not self._registry.consume(intervention_id, pending):
                return self._unavailable(intervention_id)
            replay_result = await self._replay_engine.resume(
                pending.capability,
                pending.checkpoint,
                pending.revealed_inputs(),
                resumed_context,
            )
            if replay_result.checkpoint is not None:
                return await self.suspend_for_intervention(
                    intervention_id=f"intervention-{uuid4().hex}",
                    replay_result=replay_result,
                    capability=pending.capability,
                    runtime_inputs=pending.revealed_inputs(),
                    context=resumed_context,
                )
            outcome = (
                replay_result.outcome
                if replay_result.outcome in {"SUCCESS", "BUSINESS_OUTCOME"}
                else "FAILURE"
            )
            return self._result(
                outcome,
                replay_result.reason_code or replay_result.outcome,
                replay_result.summary,
                replay_result=replay_result,
                generation_before=pending.checkpoint.suspended_generation,
                generation_after=resumed_context.expected_generation,
            )

    def _unavailable(self, intervention_id: str) -> ReplayContinuationResult:
        if self._registry.was_consumed(intervention_id):
            return self._result(
                "CONTINUATION_ALREADY_CONSUMED",
                "CONTINUATION_ALREADY_CONSUMED",
                "Replay continuation was already consumed.",
            )
        return self._result(
            "INVALID_CONTINUATION",
            "CONTINUATION_NOT_FOUND",
            "Replay continuation was not found.",
        )

    @staticmethod
    def _transition_failure(
        transition: InterventionResult,
        checkpoint: ReplayCheckpoint,
    ) -> ReplayContinuationResult:
        if transition.outcome == "SESSION_STOPPED":
            outcome = "SESSION_STOPPED"
        elif transition.outcome == "VALIDATION_FAILED":
            outcome = "VALIDATION_FAILED"
        else:
            outcome = "FAILURE"
        return ReplayContinuationCoordinator._result(
            outcome,
            transition.reason_code,
            transition.summary,
            intervention=transition.record,
            generation_before=checkpoint.suspended_generation,
        )

    @staticmethod
    def _result(
        outcome: str,
        reason_code: str,
        summary: str,
        *,
        intervention: InterventionRecord | None = None,
        replay_result: ReplayResult | None = None,
        generation_before: int | None = None,
        generation_after: int | None = None,
    ) -> ReplayContinuationResult:
        return ReplayContinuationResult.model_validate(
            {
                "outcome": outcome,
                "reason_code": reason_code,
                "summary": summary,
                "intervention": intervention,
                "replay_result": replay_result,
                "generation_before": generation_before,
                "generation_after": generation_after,
            }
        )
