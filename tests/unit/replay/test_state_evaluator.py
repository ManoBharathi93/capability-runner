from __future__ import annotations

import json
from pathlib import Path

import pytest

from capability_runner.capabilities.capability_validator import CapabilityValidator
from capability_runner.contracts.capabilities import BusinessOutcomeRule, CapabilityDefinition
from capability_runner.contracts.conditions import (
    TargetTextContains,
    TargetTextEquals,
    TargetVisible,
)
from capability_runner.contracts.evaluation import (
    EvaluationSnapshot,
    TargetObservation,
    TargetObservationState,
)
from capability_runner.contracts.surfaces import LiteralValue, SemanticTargetRef
from capability_runner.replay.state_evaluator import (
    ConditionResult,
    EvaluationErrorCode,
    StateEvaluator,
    TerminalState,
)


def _capability() -> CapabilityDefinition:
    payload = json.loads(
        Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json").read_text(
            encoding="utf-8"
        )
    )
    return CapabilityValidator().validate(CapabilityDefinition.model_validate(payload)).definition


def _snapshot(*observations: TargetObservation) -> EvaluationSnapshot:
    return EvaluationSnapshot(observed_targets=observations)


def _target(
    value: str,
    state: TargetObservationState = "VISIBLE",
    text: str | None = None,
) -> TargetObservation:
    return TargetObservation(target=SemanticTargetRef(value=value), state=state, text=text)


def test_conditions_have_explicit_true_false_and_unknown_results() -> None:
    evaluator = StateEvaluator()
    visible = TargetVisible(target=SemanticTargetRef(value="member.account.balance"))
    equals = TargetTextEquals(
        target=SemanticTargetRef(value="member.account.type"),
        expected=LiteralValue(kind="literal", value="Savings"),
    )
    contains = TargetTextContains(
        target=SemanticTargetRef(value="member.account.type"),
        expected=LiteralValue(kind="literal", value="aving"),
    )

    assert (
        evaluator.evaluate_condition(
            visible, _snapshot(_target("member.account.balance")), {}
        ).result
        == ConditionResult.TRUE
    )
    assert (
        evaluator.evaluate_condition(
            visible, _snapshot(_target("member.account.balance", "NOT_VISIBLE")), {}
        ).result
        == ConditionResult.FALSE
    )
    assert (
        evaluator.evaluate_condition(
            visible, _snapshot(_target("member.account.balance", "UNAVAILABLE")), {}
        ).result
        == ConditionResult.UNKNOWN
    )
    assert (
        evaluator.evaluate_condition(
            equals, _snapshot(_target("member.account.type", text=" Savings ")), {}
        ).result
        == ConditionResult.TRUE
    )
    assert (
        evaluator.evaluate_condition(
            equals, _snapshot(_target("member.account.type", text="Checking")), {}
        ).result
        == ConditionResult.FALSE
    )
    assert (
        evaluator.evaluate_condition(
            contains, _snapshot(_target("member.account.type", text="Savings")), {}
        ).result
        == ConditionResult.TRUE
    )
    assert (
        evaluator.evaluate_condition(
            contains, _snapshot(_target("member.account.type", text="Checking")), {}
        ).result
        == ConditionResult.FALSE
    )


def test_input_conditions_are_in_memory_and_missing_values_are_safe() -> None:
    definition = _capability()
    condition = definition.success_conditions[0]
    sentinel = "MEMBER_STATE_PRIVATE_39271"
    evaluator = StateEvaluator()

    matched = evaluator.evaluate_condition(
        condition,
        _snapshot(_target("member.details.identity", text=sentinel)),
        {"member_id": sentinel},
    )
    missing = evaluator.evaluate_condition(
        condition, _snapshot(_target("member.details.identity", text="x")), {}
    )

    assert matched.result == ConditionResult.TRUE
    assert missing.result == ConditionResult.UNKNOWN
    assert missing.issue is not None
    assert missing.issue.code == EvaluationErrorCode.RUNTIME_INPUT_MISSING
    assert sentinel not in repr(missing)


def test_real_fixture_success_extracts_declared_outputs_without_mutation() -> None:
    definition = _capability()
    runtime_inputs = {"member_id": "12345"}
    snapshot = _snapshot(
        _target("member.details.identity", text="12345"),
        _target("member.account.type", text="Savings"),
        _target("member.account.balance", text="$4,382.21 USD"),
        _target("member.search.not_found", "NOT_VISIBLE"),
    )
    evaluator = StateEvaluator()

    terminal = evaluator.evaluate_terminal_state(definition, snapshot, runtime_inputs)
    outputs = evaluator.extract_outputs(definition, snapshot)

    assert terminal.state == TerminalState.SUCCESS
    assert outputs.issue is None
    assert outputs.outputs[0].value == 438221
    assert isinstance(outputs.outputs[0].value, int)
    assert outputs.outputs[1].value == "USD"
    assert runtime_inputs == {"member_id": "12345"}
    assert snapshot.observed_targets[0].text == "12345"


def test_wrong_entity_with_valid_looking_balance_is_not_false_success() -> None:
    terminal = StateEvaluator().evaluate_terminal_state(
        _capability(),
        _snapshot(
            _target("member.details.identity", text="67890"),
            _target("member.account.type", text="Savings"),
            _target("member.account.balance", text="$4,382.21 USD"),
            _target("member.search.not_found", "NOT_VISIBLE"),
        ),
        {"member_id": "12345"},
    )

    assert terminal.state == TerminalState.INCOMPLETE
    assert terminal.success_conditions == ConditionResult.FALSE


def test_declared_business_outcome_is_not_an_evaluation_failure() -> None:
    result = StateEvaluator().evaluate_terminal_state(
        _capability(),
        _snapshot(_target("member.search.not_found")),
        {"member_id": "12345"},
    )

    assert result.state == TerminalState.BUSINESS_OUTCOME
    assert result.business_outcome_code == "MEMBER_NOT_FOUND"


@pytest.mark.parametrize(("text", "expected"), [("$4,382.21", 438221), ("$987.65", 98765)])
def test_currency_minor_unit_parser_is_decimal_based(text: str, expected: int) -> None:
    definition = _capability().model_copy(update={"outputs": (_capability().outputs[0],)})
    result = StateEvaluator().extract_outputs(
        definition,
        _snapshot(_target("member.account.balance", text=text)),
    )

    assert result.issue is None
    assert result.outputs[0].value == expected
    assert isinstance(result.outputs[0].value, int)


@pytest.mark.parametrize(
    ("state", "text", "error"),
    [
        ("VISIBLE", "not money", EvaluationErrorCode.OUTPUT_PARSE_FAILED),
        ("VISIBLE", None, EvaluationErrorCode.OUTPUT_TEXT_MISSING),
        ("UNAVAILABLE", None, EvaluationErrorCode.OUTPUT_TARGET_UNAVAILABLE),
    ],
)
def test_output_extraction_fails_closed(
    state: TargetObservationState,
    text: str | None,
    error: EvaluationErrorCode,
) -> None:
    definition = _capability().model_copy(update={"outputs": (_capability().outputs[0],)})
    result = StateEvaluator().extract_outputs(
        definition,
        _snapshot(_target("member.account.balance", state, text)),
    )

    assert result.issue is not None
    assert result.issue.code == error


def test_output_target_not_observed_and_type_mismatch_fail_closed() -> None:
    definition = _capability().model_copy(update={"outputs": (_capability().outputs[0],)})
    evaluator = StateEvaluator()
    unobserved = evaluator.extract_outputs(definition, _snapshot())
    incompatible = definition.model_copy(
        update={"outputs": (definition.outputs[0].model_copy(update={"value_type": "STRING"}),)}
    )
    mismatch = evaluator.extract_outputs(
        incompatible,
        _snapshot(_target("member.account.balance", text="$987.65")),
    )

    assert unobserved.issue is not None
    assert unobserved.issue.code == EvaluationErrorCode.OUTPUT_TARGET_UNAVAILABLE
    assert mismatch.issue is not None
    assert mismatch.issue.code == EvaluationErrorCode.OUTPUT_TYPE_MISMATCH


def test_unknown_and_conflicting_terminal_states_are_explicit() -> None:
    definition = _capability()
    evaluator = StateEvaluator()
    unknown = evaluator.evaluate_terminal_state(
        definition,
        _snapshot(_target("member.details.identity", "UNAVAILABLE")),
        {"member_id": "12345"},
    )
    conflict = evaluator.evaluate_terminal_state(
        definition,
        _snapshot(
            _target("member.details.identity", text="12345"),
            _target("member.account.type", text="Savings"),
            _target("member.account.balance", text="$4,382.21 USD"),
            _target("member.search.not_found"),
        ),
        {"member_id": "12345"},
    )

    assert unknown.state == TerminalState.UNKNOWN
    assert conflict.state == TerminalState.CONFLICT
    assert conflict.issue is not None
    assert conflict.issue.code == EvaluationErrorCode.TERMINAL_STATE_CONFLICT


def test_multiple_matching_business_outcomes_and_condition_order_are_deterministic() -> None:
    definition = _capability()
    duplicate_match = BusinessOutcomeRule(
        code="SECOND_MATCH",
        description="An intentionally conflicting test outcome.",
        conditions=(TargetVisible(target=SemanticTargetRef(value="member.search.not_found")),),
    )
    conflicting = definition.model_copy(
        update={"business_outcomes": (*definition.business_outcomes, duplicate_match)}
    )
    reordered = definition.model_copy(
        update={"success_conditions": tuple(reversed(definition.success_conditions))}
    )
    snapshot = _snapshot(
        _target("member.details.identity", text="12345"),
        _target("member.account.type", text="Savings"),
        _target("member.account.balance", text="$4,382.21 USD"),
        _target("member.search.not_found", "NOT_VISIBLE"),
    )
    evaluator = StateEvaluator()

    multiple_outcomes = evaluator.evaluate_terminal_state(
        conflicting,
        _snapshot(_target("member.search.not_found")),
        {"member_id": "12345"},
    )
    original = evaluator.evaluate_terminal_state(definition, snapshot, {"member_id": "12345"})
    reordered_result = evaluator.evaluate_terminal_state(
        reordered, snapshot, {"member_id": "12345"}
    )

    assert multiple_outcomes.state == TerminalState.CONFLICT
    assert original == reordered_result
