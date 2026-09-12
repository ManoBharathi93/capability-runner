"""Structural validation for reusable capability definitions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from capability_runner.contracts.capabilities import CapabilityDefinition, CapabilityStep
from capability_runner.contracts.conditions import (
    ConditionSpec,
    TargetTextContains,
    TargetTextEquals,
)
from capability_runner.contracts.surfaces import InputValueRef


class CapabilityValidationError(ValueError):
    """Raised when a definition fails cross-reference validation."""


@dataclass(frozen=True, slots=True)
class ValidatedCapability:
    definition: CapabilityDefinition


class CapabilityValidator:
    """Validate bounded declarative references without inspecting live profiles."""

    def validate(self, definition: CapabilityDefinition) -> ValidatedCapability:
        errors: list[str] = []
        self._validate_unique("input", (item.name for item in definition.inputs), errors)
        self._validate_unique("output", (item.name for item in definition.outputs), errors)
        self._validate_unique("step", (step.step_id for step in definition.steps), errors)
        self._validate_unique(
            "business outcome",
            (outcome.code for outcome in definition.business_outcomes),
            errors,
        )
        if not definition.success_conditions:
            errors.append("at least one success condition is required")

        input_names = {item.name for item in definition.inputs}
        for step in definition.steps:
            self._validate_step(step, input_names, errors)
        for condition in definition.success_conditions:
            self._validate_condition(condition, input_names, errors)
        for outcome in definition.business_outcomes:
            for condition in outcome.conditions:
                self._validate_condition(condition, input_names, errors)
        for item in definition.inputs:
            if item.min_length is not None and item.max_length is not None:
                if item.min_length > item.max_length:
                    errors.append(f"input {item.name} has min_length above max_length")

        if errors:
            raise CapabilityValidationError("; ".join(errors))
        return ValidatedCapability(definition=definition)

    @staticmethod
    def _validate_unique(label: str, values: Iterable[str], errors: list[str]) -> None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                errors.append(f"duplicate {label} name: {value}")
            seen.add(value)

    def _validate_step(
        self,
        step: CapabilityStep,
        input_names: set[str],
        errors: list[str],
    ) -> None:
        if step.action.kind == "fill":
            self._validate_value_source(step.action.value, input_names, errors)
        if step.precondition is not None:
            self._validate_condition(step.precondition, input_names, errors)
        if step.postcondition is not None:
            self._validate_condition(step.postcondition, input_names, errors)

    def _validate_condition(
        self,
        condition: ConditionSpec,
        input_names: set[str],
        errors: list[str],
    ) -> None:
        if isinstance(condition, (TargetTextEquals, TargetTextContains)):
            self._validate_value_source(condition.expected, input_names, errors)

    @staticmethod
    def _validate_value_source(value: object, input_names: set[str], errors: list[str]) -> None:
        if isinstance(value, InputValueRef) and value.name not in input_names:
            errors.append(f"unknown input reference: {value.name}")
