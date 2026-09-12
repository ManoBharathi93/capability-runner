"""Pure deterministic evaluation of capability state snapshots."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from capability_runner.contracts.capabilities import CapabilityDefinition, CapabilityOutput
from capability_runner.contracts.conditions import (
    ConditionSpec,
    TargetTextEquals,
    TargetVisible,
)
from capability_runner.contracts.evaluation import EvaluationSnapshot, TargetObservation
from capability_runner.contracts.surfaces import LiteralValue, TargetValueRef


class ConditionResult(StrEnum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class TerminalState(StrEnum):
    SUCCESS = "SUCCESS"
    BUSINESS_OUTCOME = "BUSINESS_OUTCOME"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class EvaluationErrorCode(StrEnum):
    RUNTIME_INPUT_MISSING = "RUNTIME_INPUT_MISSING"
    TARGET_NOT_OBSERVED = "TARGET_NOT_OBSERVED"
    OUTPUT_TARGET_UNAVAILABLE = "OUTPUT_TARGET_UNAVAILABLE"
    OUTPUT_TEXT_MISSING = "OUTPUT_TEXT_MISSING"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"
    OUTPUT_TYPE_MISMATCH = "OUTPUT_TYPE_MISMATCH"
    TERMINAL_STATE_CONFLICT = "TERMINAL_STATE_CONFLICT"
    UNSUPPORTED_PARSER = "UNSUPPORTED_PARSER"


@dataclass(frozen=True, slots=True)
class EvaluationIssue:
    code: EvaluationErrorCode
    summary: str


@dataclass(frozen=True, slots=True)
class ConditionEvaluation:
    result: ConditionResult
    issue: EvaluationIssue | None = None


@dataclass(frozen=True, slots=True)
class TerminalEvaluation:
    state: TerminalState
    success_conditions: ConditionResult
    business_outcome_code: str | None = None
    issue: EvaluationIssue | None = None


@dataclass(frozen=True, slots=True)
class ExtractedOutput:
    name: str
    value: str | int


@dataclass(frozen=True, slots=True)
class OutputExtraction:
    outputs: tuple[ExtractedOutput, ...] = ()
    issue: EvaluationIssue | None = None


_MONEY_PATTERN = re.compile(
    r"^\$?((?:0|[1-9]\d{0,2}(?:,\d{3})*|[1-9]\d*))\.(\d{2})(?:\s+[A-Z]{3})?$"
)
_CURRENCY_CODE_PATTERN = re.compile(r"^(?:[A-Z]{3}|.+\s+([A-Z]{3}))$")


class StateEvaluator:
    """Evaluate declared conditions and outputs without obtaining observations."""

    def evaluate_condition(
        self,
        condition: ConditionSpec,
        snapshot: EvaluationSnapshot,
        runtime_inputs: Mapping[str, str],
    ) -> ConditionEvaluation:
        observation = self._find_observation(condition.target.value, snapshot)
        if observation is None:
            return self._unknown(
                EvaluationErrorCode.TARGET_NOT_OBSERVED,
                "condition target not observed",
            )
        if observation.state == "UNAVAILABLE":
            return ConditionEvaluation(result=ConditionResult.UNKNOWN)
        if isinstance(condition, TargetVisible):
            return ConditionEvaluation(
                result=ConditionResult.TRUE
                if observation.state == "VISIBLE"
                else ConditionResult.FALSE
            )
        if observation.state == "NOT_VISIBLE":
            return ConditionEvaluation(result=ConditionResult.FALSE)
        expected = self._resolve_value(condition.expected, runtime_inputs)
        if isinstance(expected, EvaluationIssue):
            return ConditionEvaluation(result=ConditionResult.UNKNOWN, issue=expected)
        if observation.text is None:
            return ConditionEvaluation(result=ConditionResult.UNKNOWN)
        observed_text = observation.text.strip()
        if isinstance(condition, TargetTextEquals):
            result = ConditionResult.TRUE if observed_text == expected else ConditionResult.FALSE
            return ConditionEvaluation(result=result)
        result = ConditionResult.TRUE if expected in observed_text else ConditionResult.FALSE
        return ConditionEvaluation(result=result)

    def evaluate_terminal_state(
        self,
        definition: CapabilityDefinition,
        snapshot: EvaluationSnapshot,
        runtime_inputs: Mapping[str, str],
    ) -> TerminalEvaluation:
        outcomes = [
            outcome.code
            for outcome in definition.business_outcomes
            if self._all_conditions(outcome.conditions, snapshot, runtime_inputs).result
            == ConditionResult.TRUE
        ]
        success = self._all_conditions(definition.success_conditions, snapshot, runtime_inputs)
        if len(outcomes) > 1 or (outcomes and success.result == ConditionResult.TRUE):
            return TerminalEvaluation(
                state=TerminalState.CONFLICT,
                success_conditions=success.result,
                issue=EvaluationIssue(
                    code=EvaluationErrorCode.TERMINAL_STATE_CONFLICT,
                    summary="declared terminal states conflict",
                ),
            )
        if outcomes:
            return TerminalEvaluation(
                state=TerminalState.BUSINESS_OUTCOME,
                success_conditions=success.result,
                business_outcome_code=outcomes[0],
            )
        if success.result == ConditionResult.TRUE:
            return TerminalEvaluation(
                state=TerminalState.SUCCESS,
                success_conditions=success.result,
            )
        if success.result == ConditionResult.UNKNOWN or self._has_unknown_outcome(
            definition, snapshot, runtime_inputs
        ):
            return TerminalEvaluation(
                state=TerminalState.UNKNOWN,
                success_conditions=success.result,
            )
        return TerminalEvaluation(
            state=TerminalState.INCOMPLETE,
            success_conditions=success.result,
        )

    def extract_outputs(
        self, definition: CapabilityDefinition, snapshot: EvaluationSnapshot
    ) -> OutputExtraction:
        extracted: list[ExtractedOutput] = []
        for output in definition.outputs:
            observation = self._find_observation(output.source.target.value, snapshot)
            if observation is None or observation.state == "NOT_VISIBLE":
                return OutputExtraction(
                    issue=EvaluationIssue(
                        EvaluationErrorCode.OUTPUT_TARGET_UNAVAILABLE,
                        f"output target unavailable: {output.name}",
                    )
                )
            if observation.state == "UNAVAILABLE":
                return OutputExtraction(
                    issue=EvaluationIssue(
                        EvaluationErrorCode.OUTPUT_TARGET_UNAVAILABLE,
                        f"output target unavailable: {output.name}",
                    )
                )
            if observation.text is None:
                return OutputExtraction(
                    issue=EvaluationIssue(
                        EvaluationErrorCode.OUTPUT_TEXT_MISSING,
                        f"output text missing: {output.name}",
                    )
                )
            parsed = self._parse_output(output, observation.text)
            if isinstance(parsed, EvaluationIssue):
                return OutputExtraction(issue=parsed)
            if not self._matches_output_type(output, parsed):
                return OutputExtraction(
                    issue=EvaluationIssue(
                        EvaluationErrorCode.OUTPUT_TYPE_MISMATCH,
                        f"output type mismatch: {output.name}",
                    )
                )
            extracted.append(ExtractedOutput(name=output.name, value=parsed))
        return OutputExtraction(outputs=tuple(extracted))

    @staticmethod
    def _find_observation(target: str, snapshot: EvaluationSnapshot) -> TargetObservation | None:
        return next(
            (item for item in snapshot.observed_targets if item.target.value == target), None
        )

    @staticmethod
    def _resolve_value(
        value: TargetValueRef, runtime_inputs: Mapping[str, str]
    ) -> str | EvaluationIssue:
        if isinstance(value, LiteralValue):
            return value.value.strip()
        if value.name not in runtime_inputs:
            return EvaluationIssue(
                EvaluationErrorCode.RUNTIME_INPUT_MISSING,
                f"runtime input missing: {value.name}",
            )
        return runtime_inputs[value.name].strip()

    def _all_conditions(
        self,
        conditions: tuple[ConditionSpec, ...],
        snapshot: EvaluationSnapshot,
        runtime_inputs: Mapping[str, str],
    ) -> ConditionEvaluation:
        evaluations = [
            self.evaluate_condition(item, snapshot, runtime_inputs) for item in conditions
        ]
        if any(item.result == ConditionResult.FALSE for item in evaluations):
            return ConditionEvaluation(result=ConditionResult.FALSE)
        unknown = next(
            (item for item in evaluations if item.result == ConditionResult.UNKNOWN),
            None,
        )
        if unknown is not None:
            return unknown
        return ConditionEvaluation(result=ConditionResult.TRUE)

    def _has_unknown_outcome(
        self,
        definition: CapabilityDefinition,
        snapshot: EvaluationSnapshot,
        runtime_inputs: Mapping[str, str],
    ) -> bool:
        return any(
            self._all_conditions(outcome.conditions, snapshot, runtime_inputs).result
            == ConditionResult.UNKNOWN
            for outcome in definition.business_outcomes
        )

    @staticmethod
    def _parse_output(output: CapabilityOutput, text: str) -> str | int | EvaluationIssue:
        normalized = text.strip()
        if output.source.parser == "text":
            return normalized
        if output.source.parser == "currency_minor_units":
            match = _MONEY_PATTERN.fullmatch(normalized)
            if match is None:
                return EvaluationIssue(
                    EvaluationErrorCode.OUTPUT_PARSE_FAILED,
                    f"output parse failed: {output.name}",
                )
            try:
                amount = Decimal(f"{match.group(1).replace(',', '')}.{match.group(2)}")
            except InvalidOperation:
                return EvaluationIssue(
                    EvaluationErrorCode.OUTPUT_PARSE_FAILED,
                    f"output parse failed: {output.name}",
                )
            return int(amount * 100)
        if output.source.parser == "currency_code":
            match = _CURRENCY_CODE_PATTERN.fullmatch(normalized)
            if match is None:
                return EvaluationIssue(
                    EvaluationErrorCode.OUTPUT_PARSE_FAILED,
                    f"output parse failed: {output.name}",
                )
            return match.group(1) or normalized
        return EvaluationIssue(
            EvaluationErrorCode.UNSUPPORTED_PARSER,
            f"unsupported output parser: {output.name}",
        )

    @staticmethod
    def _matches_output_type(output: CapabilityOutput, value: str | int) -> bool:
        return (output.value_type == "INTEGER" and isinstance(value, int)) or (
            output.value_type in {"STRING", "CURRENCY_CODE"} and isinstance(value, str)
        )

    @staticmethod
    def _unknown(code: EvaluationErrorCode, summary: str) -> ConditionEvaluation:
        return ConditionEvaluation(
            result=ConditionResult.UNKNOWN,
            issue=EvaluationIssue(code=code, summary=summary),
        )
