"""Deterministically compile a verified discovery trace into a capability."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import ValidationError

from capability_runner.capabilities.capability_validator import (
    CapabilityValidationError,
    CapabilityValidator,
    ValidatedCapability,
)
from capability_runner.contracts.capabilities import (
    ActionStep,
    CapabilityDefinition,
    CapabilityInput,
    ClickActionTemplate,
    FillActionTemplate,
)
from capability_runner.contracts.capability_building import (
    CapabilityBuildRequest,
    InputEqualitySuccessTemplate,
    LiteralEqualitySuccessTemplate,
    StepReplayMetadata,
)
from capability_runner.contracts.conditions import (
    ConditionSpec,
    TargetTextEquals,
    TargetVisible,
)
from capability_runner.contracts.discovery import DiscoveryTraceEntry, GoalSpanValueSource
from capability_runner.contracts.surfaces import InputValueRef, LiteralValue, SemanticTargetRef

BuildErrorCode = Literal[
    "DISCOVERY_NOT_SUCCESSFUL",
    "TRACE_ACTION_NOT_EXECUTED",
    "BUILD_INPUT_NAME_CONFLICT",
    "BUILD_INPUT_SPEC_INVALID",
    "BUILD_COMPLETION_EVIDENCE_MISSING",
    "BUILD_OUTPUT_SPEC_INVALID",
    "BUILD_METADATA_INVALID",
    "BUILD_VALIDATION_FAILED",
]


class CapabilityBuildError(ValueError):
    def __init__(self, code: BuildErrorCode, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


class CapabilityBuilder:
    def __init__(self, validator: CapabilityValidator | None = None) -> None:
        self._validator = validator or CapabilityValidator()

    def build(self, request: CapabilityBuildRequest) -> ValidatedCapability:
        if (
            request.discovery_result.outcome != "SUCCESS"
            or request.discovery_result.reason_code != "COMPLETED"
            or not request.discovery_result.completion_evidence
            or not any(
                item.decision_kind == "COMPLETE" and item.outcome == "VERIFIED"
                for item in request.discovery_result.trace
            )
            or any(
                item.decision_kind in {"FAIL", "REQUEST_INTERVENTION"}
                for item in request.discovery_result.trace
            )
        ):
            raise CapabilityBuildError(
                "DISCOVERY_NOT_SUCCESSFUL",
                "Capability building requires a verified successful discovery result.",
            )

        action_entries = tuple(
            item for item in request.discovery_result.trace if item.decision_kind == "ACT"
        )
        if any(item.gateway_outcome != "EXECUTED" for item in action_entries):
            raise CapabilityBuildError(
                "TRACE_ACTION_NOT_EXECUTED",
                "Every compiled trace action must have an executed gateway outcome.",
            )
        if len(action_entries) != request.discovery_result.actions:
            raise CapabilityBuildError(
                "TRACE_ACTION_NOT_EXECUTED",
                "Discovery action count does not match its executed trace.",
            )

        sensitivity = self._sensitivity_map(request)
        input_names, inputs = self._build_inputs(action_entries, sensitivity)
        if set(sensitivity) != set(input_names):
            raise CapabilityBuildError(
                "BUILD_INPUT_SPEC_INVALID",
                "Input sensitivity metadata must exactly match discovered fill targets.",
            )
        step_metadata = self._step_metadata_map(request)
        steps = self._build_steps(action_entries, input_names, step_metadata)
        if step_metadata:
            raise CapabilityBuildError(
                "BUILD_METADATA_INVALID",
                "Step metadata did not match an executed discovery action.",
            )

        completion = {item.target: item for item in request.discovery_result.completion_evidence}
        success_conditions = self._build_success_conditions(
            request,
            input_names,
        )
        for output in request.outputs:
            if output.source.target.value not in completion:
                raise CapabilityBuildError(
                    "BUILD_OUTPUT_SPEC_INVALID",
                    "An output source lacks verified completion evidence.",
                )

        try:
            definition = CapabilityDefinition(
                schema_version=1,
                capability_id=request.capability_id,
                capability_version=request.capability_version,
                name=request.name,
                description=request.description,
                application_requirement=request.application_requirement,
                inputs=tuple(inputs),
                outputs=request.outputs,
                steps=tuple(steps),
                success_conditions=tuple(success_conditions),
                business_outcomes=request.business_outcomes,
            )
            return self._validator.validate(definition)
        except (ValidationError, CapabilityValidationError) as error:
            raise CapabilityBuildError(
                "BUILD_VALIDATION_FAILED",
                "Generated capability failed validation.",
            ) from error

    @staticmethod
    def _sensitivity_map(request: CapabilityBuildRequest) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for declaration in request.input_sensitivity:
            target = declaration.action_target.value
            if target in result:
                raise CapabilityBuildError(
                    "BUILD_INPUT_SPEC_INVALID",
                    "Input sensitivity declarations must be unique by action target.",
                )
            result[target] = declaration.sensitive
        return result

    @staticmethod
    def _build_inputs(
        action_entries: tuple[DiscoveryTraceEntry, ...],
        sensitivity: dict[str, bool],
    ) -> tuple[dict[str, str], list[CapabilityInput]]:
        input_names: dict[str, str] = {}
        name_sources: dict[str, GoalSpanValueSource] = {}
        inputs: list[CapabilityInput] = []
        for entry in action_entries:
            if entry.action_kind != "fill":
                continue
            if entry.semantic_target is None or entry.value_source is None:
                raise CapabilityBuildError(
                    "BUILD_INPUT_SPEC_INVALID",
                    "Executed fill actions require goal-span provenance.",
                )
            target = entry.semantic_target
            input_name = _derive_input_name(target)
            prior_source = name_sources.get(input_name)
            if prior_source is not None and prior_source != entry.value_source:
                raise CapabilityBuildError(
                    "BUILD_INPUT_NAME_CONFLICT",
                    "Distinct goal-span values derived the same capability input name.",
                )
            if target in input_names:
                continue
            if target not in sensitivity:
                raise CapabilityBuildError(
                    "BUILD_INPUT_SPEC_INVALID",
                    "A discovered input lacks trusted sensitivity metadata.",
                )
            input_names[target] = input_name
            name_sources[input_name] = entry.value_source
            if not any(item.name == input_name for item in inputs):
                inputs.append(
                    CapabilityInput(
                        name=input_name,
                        value_type="STRING",
                        required=True,
                        sensitive=sensitivity[target],
                    )
                )
        return input_names, inputs

    @staticmethod
    def _step_metadata_map(
        request: CapabilityBuildRequest,
    ) -> dict[tuple[str, str, int], StepReplayMetadata]:
        result: dict[tuple[str, str, int], StepReplayMetadata] = {}
        for metadata in request.step_metadata:
            key = (metadata.action_kind, metadata.target.value, metadata.occurrence)
            if key in result:
                raise CapabilityBuildError(
                    "BUILD_METADATA_INVALID",
                    "Step metadata selectors must be unique.",
                )
            result[key] = metadata
        return result

    @staticmethod
    def _build_steps(
        entries: tuple[DiscoveryTraceEntry, ...],
        input_names: dict[str, str],
        metadata: dict[tuple[str, str, int], StepReplayMetadata],
    ) -> list[ActionStep]:
        steps: list[ActionStep] = []
        step_ids: dict[str, int] = {}
        occurrences: dict[tuple[str, str], int] = {}
        for entry in entries:
            assert entry.action_kind is not None
            assert entry.semantic_target is not None
            target = SemanticTargetRef(value=entry.semantic_target)
            occurrence_key = (entry.action_kind, entry.semantic_target)
            occurrence = occurrences.get(occurrence_key, 0) + 1
            occurrences[occurrence_key] = occurrence
            trusted_step = metadata.pop(
                (entry.action_kind, entry.semantic_target, occurrence),
                None,
            )
            base_step_id = f"{entry.action_kind}_{entry.semantic_target.replace('.', '_')}"
            ordinal = step_ids.get(base_step_id, 0) + 1
            step_ids[base_step_id] = ordinal
            step_id = base_step_id if ordinal == 1 else f"{base_step_id}_{ordinal}"
            if entry.action_kind == "fill":
                input_name = input_names[entry.semantic_target]
                action = FillActionTemplate(
                    target=target,
                    value=InputValueRef(kind="input", name=input_name),
                )
            else:
                action = ClickActionTemplate(target=target)
            steps.append(
                ActionStep(
                    step_id=step_id,
                    action=action,
                    precondition=trusted_step.precondition if trusted_step else None,
                    postcondition=trusted_step.postcondition if trusted_step else None,
                    retry_policy=trusted_step.retry_policy if trusted_step else None,
                )
            )
        return steps

    @staticmethod
    def _build_success_conditions(
        request: CapabilityBuildRequest,
        input_names: dict[str, str],
    ) -> list[ConditionSpec]:
        evidence_by_target = {
            item.target: item for item in request.discovery_result.completion_evidence
        }
        conditions: list[ConditionSpec] = []
        for template in request.success_templates:
            evidence = evidence_by_target.get(template.target.value)
            if evidence is None:
                raise CapabilityBuildError(
                    "BUILD_COMPLETION_EVIDENCE_MISSING",
                    "A success template lacks verified completion evidence.",
                )
            if isinstance(template, InputEqualitySuccessTemplate):
                source_target = template.input_action_target.value
                input_name = input_names.get(source_target)
                if input_name is None or evidence.goal_span_action_target != source_target:
                    raise CapabilityBuildError(
                        "BUILD_COMPLETION_EVIDENCE_MISSING",
                        "Identity evidence is not linked to the declared input source.",
                    )
                conditions.append(
                    TargetTextEquals(
                        target=template.target,
                        expected=InputValueRef(kind="input", name=input_name),
                    )
                )
            elif isinstance(template, LiteralEqualitySuccessTemplate):
                if evidence.text_fingerprint != _text_fingerprint(template.expected):
                    raise CapabilityBuildError(
                        "BUILD_COMPLETION_EVIDENCE_MISSING",
                        "Literal success metadata does not match verified completion evidence.",
                    )
                conditions.append(
                    TargetTextEquals(
                        target=template.target,
                        expected=LiteralValue(kind="literal", value=template.expected),
                    )
                )
            else:
                conditions.append(TargetVisible(target=template.target))
        return conditions


def _derive_input_name(semantic_target: str) -> str:
    candidate = semantic_target.rsplit(".", 1)[-1]
    try:
        CapabilityInput(name=candidate, value_type="STRING")
    except ValidationError as error:
        raise CapabilityBuildError(
            "BUILD_INPUT_SPEC_INVALID",
            "Derived capability input name is invalid.",
        ) from error
    return candidate


def _text_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
