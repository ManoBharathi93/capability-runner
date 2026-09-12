"""Model-free, gateway-mediated execution of a validated capability."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping
from typing import Protocol

from pydantic import SecretStr

from capability_runner.capabilities.capability_validator import ValidatedCapability
from capability_runner.contracts.actions import ClickAction, FillAction
from capability_runner.contracts.capabilities import (
    CapabilityActionTemplate,
    CapabilityDefinition,
    CapabilityInput,
    FillActionTemplate,
)
from capability_runner.contracts.evaluation import EvaluationSnapshot
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import GatewayActionRequest, GatewayExecutionContext
from capability_runner.contracts.intervention import ResumeValidationResult
from capability_runner.contracts.replay import ReplayCheckpoint, ReplayResult
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    InputValueRef,
    SemanticTargetRef,
    SurfaceSessionRef,
)
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.interaction.action_gateway import ActionGateway

from .snapshot_collector import SnapshotCollectionError, SnapshotCollector
from .state_evaluator import ConditionResult, EvaluationErrorCode, StateEvaluator, TerminalState


class EvidenceWriter(Protocol):
    def record(self, event: EvidenceEvent) -> object: ...


class ReplayEngine:
    def __init__(
        self,
        *,
        action_gateway: ActionGateway,
        snapshot_collector: SnapshotCollector,
        state_evaluator: StateEvaluator,
        evidence_recorder: EvidenceWriter | None = None,
    ) -> None:
        self._action_gateway = action_gateway
        self._snapshot_collector = snapshot_collector
        self._state_evaluator = state_evaluator
        self._evidence_recorder = evidence_recorder

    async def replay(
        self,
        capability: ValidatedCapability,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ReplayResult:
        definition = capability.definition
        self._record_event(
            context,
            reason_code="REPLAY_STARTED",
            outcome="started",
            metadata={
                "capability_id": definition.capability_id,
                "capability_version": definition.capability_version,
                "input_names": sorted(runtime_inputs),
                "start_step_index": 0,
            },
        )
        input_error = self._validate_inputs(definition.inputs, runtime_inputs)
        if input_error is not None:
            result = self._failure(context.run_id, input_error, "Runtime inputs are invalid.")
            self._record_completed(context, definition, result)
            return result
        profile_error = self._validate_profile(definition, context.profile)
        if profile_error is not None:
            result = self._failure(
                context.run_id, profile_error, "Trusted profile is incompatible."
            )
            self._record_completed(context, definition, result)
            return result
        result = await self._execute_steps(definition, runtime_inputs, context, start_index=0)
        self._record_completed(context, definition, result)
        return result

    async def resume(
        self,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ReplayResult:
        definition = capability.definition
        self._record_event(
            context,
            reason_code="REPLAY_RESUME_STARTED",
            outcome="started",
            step_id=checkpoint.blocked_step_id,
            metadata={
                "action_effect_state": checkpoint.action_effect_state,
                "blocked_step_id": checkpoint.blocked_step_id,
                "blocked_step_index": checkpoint.blocked_step_index,
                "capability_id": definition.capability_id,
                "capability_version": definition.capability_version,
                "checkpoint_generation": checkpoint.suspended_generation,
                "current_generation": context.expected_generation,
                "input_names": sorted(runtime_inputs),
            },
        )
        result = await self._resume(capability, checkpoint, runtime_inputs, context)
        self._record_completed(context, definition, result)
        return result

    async def _resume(
        self,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ReplayResult:
        definition = capability.definition
        input_error = self._validate_inputs(definition.inputs, runtime_inputs)
        if input_error is not None:
            return self._failure(context.run_id, input_error, "Runtime inputs are invalid.")
        profile_error = self._validate_profile(definition, context.profile)
        if profile_error is not None:
            return self._failure(context.run_id, profile_error, "Trusted profile is incompatible.")
        checkpoint_error = self._validate_checkpoint_identity(definition, checkpoint)
        if (
            checkpoint_error is None
            and context.expected_generation <= checkpoint.suspended_generation
        ):
            checkpoint_error = "STALE_GENERATION"
        if checkpoint_error is not None:
            return self._failure(
                context.run_id,
                checkpoint_error,
                "Replay checkpoint is not valid for this continuation.",
                checkpoint.blocked_step_id,
                checkpoint.blocked_step_index,
            )

        targets = self._targets_for(definition)
        current = await self._collect(
            context.surface_session,
            context.profile,
            targets,
            context.run_id,
            checkpoint.blocked_step_id,
            checkpoint.blocked_step_index,
        )
        if isinstance(current, ReplayResult):
            return current
        start_index, current_result = self._resume_position(
            definition,
            checkpoint,
            current,
            runtime_inputs,
            context.run_id,
        )
        if current_result is not None:
            return current_result
        assert start_index is not None
        return await self._execute_steps(
            definition,
            runtime_inputs,
            context,
            start_index=start_index,
        )

    async def validate_resume(
        self,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ResumeValidationResult:
        definition = capability.definition
        input_error = self._validate_inputs(definition.inputs, runtime_inputs)
        profile_error = self._validate_profile(definition, context.profile)
        checkpoint_error = self._validate_checkpoint_identity(definition, checkpoint)
        validation_error = input_error or profile_error or checkpoint_error
        if validation_error is not None:
            return ResumeValidationResult(
                outcome="INVALID",
                reason_code=validation_error,
                summary="Replay continuation state is invalid.",
            )
        current = await self._collect(
            context.surface_session,
            context.profile,
            self._targets_for(definition),
            context.run_id,
            checkpoint.blocked_step_id,
            checkpoint.blocked_step_index,
        )
        if isinstance(current, ReplayResult):
            return ResumeValidationResult(
                outcome="INVALID",
                reason_code=current.reason_code or "RESUME_STATE_UNVERIFIED",
                summary="Fresh replay state could not be collected.",
            )
        _, current_result = self._resume_position(
            definition,
            checkpoint,
            current,
            runtime_inputs,
            context.run_id,
        )
        if current_result is not None and current_result.outcome == "FAILURE":
            return ResumeValidationResult(
                outcome="INVALID",
                reason_code=current_result.reason_code or "RESUME_STATE_UNVERIFIED",
                summary="Fresh replay state is not safe to continue.",
            )
        return ResumeValidationResult(
            outcome="VALID",
            reason_code=(
                "CURRENT_TERMINAL_STATE_CONFIRMED"
                if current_result is not None
                else "CURRENT_STEP_STATE_CONFIRMED"
            ),
            summary=(
                "Fresh terminal replay state was confirmed."
                if current_result is not None
                else "Fresh blocked-step state was confirmed."
            ),
        )

    async def _execute_steps(
        self,
        definition: CapabilityDefinition,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
        *,
        start_index: int,
    ) -> ReplayResult:
        target = ProfileTarget(
            kind="profile",
            application=context.profile.application_family,
            profile=context.profile.variant,
            entry_url=context.profile.entry_point,
        )
        for step_index in range(start_index, len(definition.steps)):
            step = definition.steps[step_index]
            attempted = step_index + 1
            self._record_event(
                context,
                reason_code="REPLAY_STEP_STARTED",
                outcome="started",
                step_id=step.step_id,
                metadata={
                    "action_kind": step.action.kind,
                    "has_postcondition": step.postcondition is not None,
                    "has_precondition": step.precondition is not None,
                    "semantic_target": step.action.target.value,
                    "step_index": step_index,
                },
            )
            targets = self._targets_for(definition)
            before = await self._collect(
                context.surface_session,
                context.profile,
                targets,
                context.run_id,
                step.step_id,
                attempted,
            )
            if isinstance(before, ReplayResult):
                return before
            if step.precondition is not None:
                condition = self._state_evaluator.evaluate_condition(
                    step.precondition, before, runtime_inputs
                )
                if (
                    condition.issue is not None
                    and condition.issue.code == EvaluationErrorCode.RUNTIME_INPUT_MISSING
                ):
                    return self._failure(
                        context.run_id,
                        "INVALID_INPUT",
                        "Runtime input is missing.",
                        step.step_id,
                        step_index,
                    )
                if condition.result != ConditionResult.TRUE:
                    return self._failure(
                        context.run_id,
                        "PRECONDITION_FAILED",
                        "Step precondition was not met.",
                        step.step_id,
                        step_index,
                    )
            action = self._materialize(step.action, runtime_inputs, target)
            request = GatewayActionRequest(
                action_id=f"{context.run_id}-{step.step_id}",
                semantic_target=step.action.target,
                action=action,
                step_id=step.step_id,
            )
            gateway = await self._action_gateway.execute(request, context)
            if gateway.outcome != "EXECUTED":
                checkpoint = (
                    ReplayCheckpoint(
                        capability_id=definition.capability_id,
                        capability_version=definition.capability_version,
                        blocked_step_id=step.step_id,
                        blocked_step_index=step_index,
                        suspended_generation=context.expected_generation,
                    )
                    if gateway.outcome == "APPROVAL_REQUIRED"
                    else None
                )
                self._record_event(
                    context,
                    reason_code="REPLAY_STEP_BLOCKED",
                    outcome=gateway.outcome.casefold(),
                    step_id=step.step_id,
                    action_id=request.action_id,
                    metadata={
                        "action_effect_state": (
                            checkpoint.action_effect_state if checkpoint is not None else None
                        ),
                        "gateway_reason_code": gateway.reason_code,
                        "step_index": step_index,
                    },
                )
                return self._failure(
                    context.run_id,
                    gateway.reason_code,
                    gateway.summary,
                    step.step_id,
                    attempted,
                    checkpoint,
                )
            self._record_event(
                context,
                reason_code="REPLAY_STEP_DISPATCHED",
                outcome="executed",
                step_id=step.step_id,
                action_id=request.action_id,
                metadata={"step_index": step_index},
            )
            retry_policy = step.retry_policy
            max_observations = retry_policy.max_attempts if retry_policy else 1
            postcondition_met = step.postcondition is None
            for observation_attempt in range(max_observations):
                if observation_attempt:
                    assert retry_policy is not None
                    await asyncio.sleep(retry_policy.delay_ms / 1000)
                after = await self._collect(
                    context.surface_session,
                    context.profile,
                    targets,
                    context.run_id,
                    step.step_id,
                    attempted,
                )
                if isinstance(after, ReplayResult):
                    return after
                terminal_result = self._terminal_result(
                    definition,
                    after,
                    runtime_inputs,
                    context.run_id,
                    step.step_id,
                    attempted,
                )
                if terminal_result is not None:
                    self._record_event(
                        context,
                        reason_code="REPLAY_STEP_COMPLETED",
                        outcome=terminal_result.outcome.casefold(),
                        step_id=step.step_id,
                        action_id=request.action_id,
                        metadata={"step_index": step_index},
                    )
                    return terminal_result
                if step.postcondition is not None:
                    condition = self._state_evaluator.evaluate_condition(
                        step.postcondition, after, runtime_inputs
                    )
                    if (
                        condition.issue is not None
                        and condition.issue.code == EvaluationErrorCode.RUNTIME_INPUT_MISSING
                    ):
                        return self._failure(
                            context.run_id,
                            "INVALID_INPUT",
                            "Runtime input is missing.",
                            step.step_id,
                            attempted,
                        )
                    if condition.result == ConditionResult.TRUE:
                        postcondition_met = True
                        break
                    if condition.result == ConditionResult.FALSE and retry_policy is None:
                        return self._failure(
                            context.run_id,
                            "POSTCONDITION_FAILED",
                            "Step postcondition was not met.",
                            step.step_id,
                            attempted,
                        )
            if retry_policy is not None and not postcondition_met:
                return self._failure(
                    context.run_id,
                    "STEP_TIMEOUT",
                    "Step did not reach a declared terminal state in time.",
                    step.step_id,
                    attempted,
                )
            self._record_event(
                context,
                reason_code="REPLAY_STEP_COMPLETED",
                outcome="completed",
                step_id=step.step_id,
                action_id=request.action_id,
                metadata={"step_index": step_index},
            )
        return self._failure(
            context.run_id,
            "INCOMPLETE",
            "Capability completed without declared success.",
            steps_attempted=len(definition.steps),
        )

    def _record_completed(
        self,
        context: GatewayExecutionContext,
        definition: CapabilityDefinition,
        result: ReplayResult,
    ) -> None:
        self._record_event(
            context,
            reason_code="REPLAY_COMPLETED",
            outcome=result.outcome.casefold(),
            step_id=result.step_id,
            metadata={
                "business_outcome_code": result.business_outcome_code,
                "capability_id": definition.capability_id,
                "capability_version": definition.capability_version,
                "result_reason_code": result.reason_code,
                "steps_attempted": result.steps_attempted,
            },
        )

    def _record_event(
        self,
        context: GatewayExecutionContext,
        *,
        reason_code: str,
        outcome: str,
        metadata: dict[str, object],
        step_id: str | None = None,
        action_id: str | None = None,
    ) -> None:
        if self._evidence_recorder is None:
            return
        self._evidence_recorder.record(
            EvidenceEvent(
                event_type="lifecycle",
                component="replay-engine",
                run_id=context.run_id,
                session_id=context.control_session_id,
                step_id=step_id,
                action_id=action_id,
                outcome=outcome,
                reason_code=reason_code,
                metadata=metadata,
            )
        )

    def _terminal_result(
        self,
        definition: CapabilityDefinition,
        snapshot: EvaluationSnapshot,
        runtime_inputs: Mapping[str, str],
        run_id: str,
        step_id: str,
        steps_attempted: int,
    ) -> ReplayResult | None:
        terminal = self._state_evaluator.evaluate_terminal_state(
            definition, snapshot, runtime_inputs
        )
        if terminal.state == TerminalState.BUSINESS_OUTCOME:
            return ReplayResult(
                outcome="BUSINESS_OUTCOME",
                run_id=run_id,
                business_outcome_code=terminal.business_outcome_code,
                summary="Declared business outcome reached.",
                steps_attempted=steps_attempted,
            )
        if terminal.state == TerminalState.CONFLICT:
            return self._failure(
                run_id,
                "TERMINAL_STATE_CONFLICT",
                "Declared terminal states conflict.",
                step_id,
                steps_attempted,
            )
        if terminal.state != TerminalState.SUCCESS:
            return None
        outputs = self._state_evaluator.extract_outputs(definition, snapshot)
        if outputs.issue is not None:
            return self._failure(
                run_id,
                "OUTPUT_EXTRACTION_FAILED",
                "Declared outputs could not be extracted.",
                step_id,
                steps_attempted,
            )
        return ReplayResult(
            outcome="SUCCESS",
            run_id=run_id,
            outputs={item.name: item.value for item in outputs.outputs},
            summary="Declared success conditions were met.",
            steps_attempted=steps_attempted,
        )

    def _resume_position(
        self,
        definition: CapabilityDefinition,
        checkpoint: ReplayCheckpoint,
        snapshot: EvaluationSnapshot,
        runtime_inputs: Mapping[str, str],
        run_id: str,
    ) -> tuple[int | None, ReplayResult | None]:
        terminal = self._terminal_result(
            definition,
            snapshot,
            runtime_inputs,
            run_id,
            checkpoint.blocked_step_id,
            checkpoint.blocked_step_index,
        )
        if terminal is not None:
            return None, terminal

        blocked_step = definition.steps[checkpoint.blocked_step_index]
        if blocked_step.postcondition is None:
            return None, self._failure(
                run_id,
                "RESUME_STATE_UNVERIFIED",
                "Current state does not prove whether the blocked step was completed.",
                checkpoint.blocked_step_id,
                checkpoint.blocked_step_index,
            )
        postcondition = self._state_evaluator.evaluate_condition(
            blocked_step.postcondition,
            snapshot,
            runtime_inputs,
        )
        if (
            postcondition.issue is not None
            and postcondition.issue.code == EvaluationErrorCode.RUNTIME_INPUT_MISSING
        ):
            return None, self._failure(
                run_id,
                "INVALID_INPUT",
                "Runtime input is missing.",
                checkpoint.blocked_step_id,
                checkpoint.blocked_step_index,
            )
        if postcondition.result == ConditionResult.UNKNOWN:
            return None, self._failure(
                run_id,
                "RESUME_STATE_UNVERIFIED",
                "Current state could not verify the blocked step postcondition.",
                checkpoint.blocked_step_id,
                checkpoint.blocked_step_index,
            )
        start_index = (
            checkpoint.blocked_step_index + 1
            if postcondition.result == ConditionResult.TRUE
            else checkpoint.blocked_step_index
        )
        return start_index, None

    @staticmethod
    def _validate_checkpoint_identity(
        definition: CapabilityDefinition,
        checkpoint: ReplayCheckpoint,
    ) -> str | None:
        if (
            checkpoint.capability_id != definition.capability_id
            or checkpoint.capability_version != definition.capability_version
            or checkpoint.blocked_step_index >= len(definition.steps)
            or definition.steps[checkpoint.blocked_step_index].step_id != checkpoint.blocked_step_id
        ):
            return "INVALID_REPLAY_CHECKPOINT"
        return None

    async def _collect(
        self,
        session: SurfaceSessionRef,
        profile: ApplicationProfile,
        targets: tuple[SemanticTargetRef, ...],
        run_id: str,
        step_id: str,
        attempted: int,
    ) -> EvaluationSnapshot | ReplayResult:
        try:
            return await self._snapshot_collector.collect(session, profile, targets)
        except SnapshotCollectionError as error:
            return self._failure(run_id, error.code, error.summary, step_id, attempted)

    @staticmethod
    def _validate_inputs(
        inputs: tuple[CapabilityInput, ...], runtime_inputs: Mapping[str, str]
    ) -> str | None:
        declared = {item.name for item in inputs}
        if set(runtime_inputs) - declared:
            return "INVALID_INPUT"
        for item in inputs:
            value = runtime_inputs.get(item.name)
            if value is None:
                if item.required:
                    return "RUNTIME_INPUT_MISSING"
                continue
            if (
                (item.min_length is not None and len(value) < item.min_length)
                or (item.max_length is not None and len(value) > item.max_length)
                or (item.pattern is not None and re.fullmatch(item.pattern, value) is None)
            ):
                return "INVALID_INPUT"
        return None

    @staticmethod
    def _validate_profile(
        definition: CapabilityDefinition, profile: ApplicationProfile
    ) -> str | None:
        if (
            definition.application_requirement.application_family != profile.application_family
            or definition.application_requirement.surface_kind != "browser"
        ):
            return "PROFILE_INCOMPATIBLE"
        bound = {item.semantic_target.value for item in profile.target_bindings}
        required = {item.value for item in ReplayEngine._targets_for(definition)}
        return None if required <= bound else "TARGET_BINDING_MISSING"

    @staticmethod
    def _targets_for(definition: CapabilityDefinition) -> tuple[SemanticTargetRef, ...]:
        targets: dict[str, SemanticTargetRef] = {
            output.source.target.value: output.source.target for output in definition.outputs
        }
        conditions = (
            *definition.success_conditions,
            *(
                condition
                for outcome in definition.business_outcomes
                for condition in outcome.conditions
            ),
        )
        for condition in conditions:
            targets[condition.target.value] = condition.target
        for step in definition.steps:
            targets[step.action.target.value] = step.action.target
            if step.precondition is not None:
                targets[step.precondition.target.value] = step.precondition.target
            if step.postcondition is not None:
                targets[step.postcondition.target.value] = step.postcondition.target
        return tuple(targets[key] for key in sorted(targets))

    @staticmethod
    def _materialize(
        action: CapabilityActionTemplate,
        runtime_inputs: Mapping[str, str],
        target: ProfileTarget,
    ) -> FillAction | ClickAction:
        if isinstance(action, FillActionTemplate):
            value = (
                action.value.value
                if not isinstance(action.value, InputValueRef)
                else runtime_inputs[action.value.name]
            )
            return FillAction(target=target, value=SecretStr(value))
        return ClickAction(target=target)

    @staticmethod
    def _failure(
        run_id: str,
        reason: str,
        summary: str,
        step_id: str | None = None,
        steps_attempted: int = 0,
        checkpoint: ReplayCheckpoint | None = None,
    ) -> ReplayResult:
        return ReplayResult(
            outcome="FAILURE",
            run_id=run_id,
            reason_code=reason,
            step_id=step_id,
            summary=summary,
            steps_attempted=steps_attempted,
            checkpoint=checkpoint,
        )
