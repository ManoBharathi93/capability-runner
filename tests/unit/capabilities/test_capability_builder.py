from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from capability_runner.capabilities.capability_builder import (
    CapabilityBuilder,
    CapabilityBuildError,
)
from capability_runner.capabilities.capability_store import (
    CapabilityStore,
    CapabilityVersionAlreadyExistsError,
)
from capability_runner.capabilities.capability_validator import (
    CapabilityValidationError,
    CapabilityValidator,
    ValidatedCapability,
)
from capability_runner.contracts.capabilities import (
    CapabilityDefinition,
    FillActionTemplate,
)
from capability_runner.contracts.capability_building import CapabilityBuildRequest
from capability_runner.contracts.discovery import DiscoveryResult

FIXTURE_PATH = Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json")
FINGERPRINT = "0" * 64


def _text_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _successful_result(
    member_id: str = "67890",
    balance: str = "$987.65 USD",
    *,
    include_invalid: bool = False,
    duplicate_submit: bool = False,
) -> DiscoveryResult:
    trace: list[dict[str, object]] = [
        {
            "turn": 1,
            "decision_kind": "ACT",
            "action_kind": "fill",
            "semantic_target": "member.search.member_id",
            "value_source": {"kind": "goal_span", "start": 44, "end": 49},
            "gateway_outcome": "EXECUTED",
            "observation_fingerprint": FINGERPRINT,
            "outcome": "APPLIED",
        },
        {
            "turn": 2,
            "decision_kind": "ACT",
            "action_kind": "click",
            "semantic_target": "member.search.submit",
            "gateway_outcome": "EXECUTED",
            "observation_fingerprint": FINGERPRINT,
            "outcome": "APPLIED",
        },
    ]
    if include_invalid:
        trace.append(
            {
                "turn": 3,
                "decision_kind": "INVALID",
                "observation_fingerprint": FINGERPRINT,
                "outcome": "INVALID_MODEL_RESPONSE",
            }
        )
    if duplicate_submit:
        trace.append(
            {
                "turn": 3,
                "decision_kind": "ACT",
                "action_kind": "click",
                "semantic_target": "member.search.submit",
                "gateway_outcome": "EXECUTED",
                "observation_fingerprint": FINGERPRINT,
                "outcome": "APPLIED",
            }
        )
    trace.extend(
        [
            {
                "turn": 4,
                "decision_kind": "ACT",
                "action_kind": "click",
                "semantic_target": "member.results.open",
                "gateway_outcome": "EXECUTED",
                "observation_fingerprint": FINGERPRINT,
                "outcome": "APPLIED",
            },
            {
                "turn": 5,
                "decision_kind": "ACT",
                "action_kind": "click",
                "semantic_target": "member.accounts.savings",
                "gateway_outcome": "EXECUTED",
                "observation_fingerprint": FINGERPRINT,
                "outcome": "APPLIED",
            },
            {
                "turn": 6,
                "decision_kind": "COMPLETE",
                "observation_fingerprint": FINGERPRINT,
                "outcome": "VERIFIED",
            },
        ]
    )
    action_count = sum(item["decision_kind"] == "ACT" for item in trace)
    return DiscoveryResult.model_validate(
        {
            "outcome": "SUCCESS",
            "reason_code": "COMPLETED",
            "turns": 6,
            "actions": action_count,
            "verified_targets": [
                "member.details.identity",
                "member.account.type",
                "member.account.balance",
            ],
            "completion_evidence": [
                {
                    "target": "member.details.identity",
                    "text_fingerprint": _text_fingerprint(member_id),
                    "goal_span_action_target": "member.search.member_id",
                },
                {
                    "target": "member.account.type",
                    "text_fingerprint": _text_fingerprint("Savings"),
                },
                {
                    "target": "member.account.balance",
                    "text_fingerprint": _text_fingerprint(balance),
                },
            ],
            "trace": trace,
        }
    )


def _build_request(
    result: DiscoveryResult | None = None,
    *,
    include_retry: bool = True,
) -> CapabilityBuildRequest:
    step_metadata: list[dict[str, object]] = []
    if include_retry:
        step_metadata.append(
            {
                "action_kind": "click",
                "target": {"value": "member.search.submit"},
                "postcondition": {
                    "kind": "target_visible",
                    "target": {"value": "member.results.open"},
                },
                "retry_policy": {
                    "kind": "wait_and_retry",
                    "max_attempts": 3,
                    "delay_ms": 400,
                },
            }
        )
    return CapabilityBuildRequest.model_validate(
        {
            "capability_id": "lookup_savings_balance",
            "capability_version": "1.0.0",
            "name": "Lookup savings balance",
            "description": "Find a member savings account and return its balance.",
            "discovery_result": result or _successful_result(),
            "application_requirement": {
                "application_family": "corebank",
                "surface_kind": "browser",
            },
            "input_sensitivity": [
                {
                    "action_target": {"value": "member.search.member_id"},
                    "sensitive": True,
                }
            ],
            "success_templates": [
                {
                    "kind": "input_equals",
                    "target": {"value": "member.details.identity"},
                    "input_action_target": {"value": "member.search.member_id"},
                },
                {
                    "kind": "literal_equals",
                    "target": {"value": "member.account.type"},
                    "expected": "Savings",
                },
                {
                    "kind": "target_visible",
                    "target": {"value": "member.account.balance"},
                },
            ],
            "outputs": [
                {
                    "name": "balance_minor_units",
                    "value_type": "INTEGER",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_minor_units",
                    },
                },
                {
                    "name": "currency",
                    "value_type": "CURRENCY_CODE",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_code",
                    },
                },
            ],
            "business_outcomes": [
                {
                    "code": "MEMBER_NOT_FOUND",
                    "description": "The requested member was not found.",
                    "conditions": [
                        {
                            "kind": "target_visible",
                            "target": {"value": "member.search.not_found"},
                        }
                    ],
                }
            ],
            "step_metadata": step_metadata,
        }
    )


@pytest.mark.parametrize("outcome", ["FAILED", "INTERVENTION_REQUIRED"])
def test_unsuccessful_discovery_is_rejected(outcome: str) -> None:
    result = DiscoveryResult.model_validate(
        {"outcome": outcome, "reason_code": "STOPPED", "turns": 1, "actions": 0}
    )

    with pytest.raises(CapabilityBuildError) as error:
        CapabilityBuilder().build(_build_request(result))

    assert error.value.code == "DISCOVERY_NOT_SUCCESSFUL"


def test_executed_goal_span_fill_becomes_required_sensitive_string_input() -> None:
    definition = CapabilityBuilder().build(_build_request()).definition

    assert len(definition.inputs) == 1
    assert definition.inputs[0].model_dump() == {
        "name": "member_id",
        "value_type": "STRING",
        "required": True,
        "sensitive": True,
        "min_length": None,
        "max_length": None,
        "pattern": None,
    }
    assert isinstance(definition.steps[0].action, FillActionTemplate)
    assert definition.steps[0].action.value.model_dump() == {
        "kind": "input",
        "name": "member_id",
    }


def test_discovered_runtime_values_are_absent_from_artifact() -> None:
    serialized = CapabilityBuilder().build(_build_request()).definition.model_dump_json()

    assert "67890" not in serialized
    assert "98765" not in serialized
    assert "$987.65" not in serialized


def test_click_actions_compile_in_executed_order() -> None:
    definition = CapabilityBuilder().build(_build_request()).definition

    assert [(step.action.kind, step.action.target.value) for step in definition.steps] == [
        ("fill", "member.search.member_id"),
        ("click", "member.search.submit"),
        ("click", "member.results.open"),
        ("click", "member.accounts.savings"),
    ]


def test_invalid_model_trace_entries_are_not_compiled() -> None:
    definition = CapabilityBuilder().build(
        _build_request(_successful_result(include_invalid=True))
    ).definition

    assert len(definition.steps) == 4


def test_nonexecuted_action_trace_is_rejected() -> None:
    result = _successful_result()
    failed_action = result.trace[1].model_copy(
        update={"gateway_outcome": "FAILED", "outcome": "TARGET_NOT_ACTIONABLE"}
    )
    result = result.model_copy(
        update={"trace": (result.trace[0], failed_action, *result.trace[2:])}
    )

    with pytest.raises(CapabilityBuildError) as error:
        CapabilityBuilder().build(_build_request(result))

    assert error.value.code == "TRACE_ACTION_NOT_EXECUTED"


def test_step_ids_are_deterministic_and_duplicate_ids_get_ordinals() -> None:
    definition = CapabilityBuilder().build(
        _build_request(_successful_result(duplicate_submit=True))
    ).definition

    assert [step.step_id for step in definition.steps] == [
        "fill_member_search_member_id",
        "click_member_search_submit",
        "click_member_search_submit_2",
        "click_member_results_open",
        "click_member_accounts_savings",
    ]


def test_distinct_goal_spans_with_same_derived_name_are_rejected() -> None:
    result = _successful_result()
    second_fill_data = result.trace[0].model_dump(mode="json")
    second_fill_data.update(
        {
            "turn": 2,
            "semantic_target": "alternate.member_id",
            "value_source": {"kind": "goal_span", "start": 10, "end": 15},
        }
    )
    second_fill = type(result.trace[0]).model_validate(second_fill_data)
    result = result.model_copy(
        update={"actions": 5, "trace": (result.trace[0], second_fill, *result.trace[1:])}
    )
    request_data = _build_request(result).model_dump(mode="json")
    request_data["input_sensitivity"].append(
        {
            "action_target": {"value": "alternate.member_id"},
            "sensitive": True,
        }
    )

    with pytest.raises(CapabilityBuildError) as error:
        CapabilityBuilder().build(CapabilityBuildRequest.model_validate(request_data))

    assert error.value.code == "BUILD_INPUT_NAME_CONFLICT"


def test_identity_template_requires_verified_input_relationship() -> None:
    result = _successful_result()
    evidence = result.completion_evidence[0].model_copy(
        update={"goal_span_action_target": None}
    )
    result = result.model_copy(
        update={"completion_evidence": (evidence, *result.completion_evidence[1:])}
    )

    with pytest.raises(CapabilityBuildError) as error:
        CapabilityBuilder().build(_build_request(result))

    assert error.value.code == "BUILD_COMPLETION_EVIDENCE_MISSING"


def test_fixed_success_condition_requires_matching_verified_value() -> None:
    request = _build_request()
    templates = list(request.success_templates)
    templates[1] = templates[1].model_copy(update={"expected": "Checking"})

    with pytest.raises(CapabilityBuildError) as error:
        CapabilityBuilder().build(request.model_copy(update={"success_templates": templates}))

    assert error.value.code == "BUILD_COMPLETION_EVIDENCE_MISSING"


def test_success_templates_compile_identity_literal_and_visible_conditions() -> None:
    conditions = CapabilityBuilder().build(_build_request()).definition.success_conditions

    assert [item.kind for item in conditions] == [
        "target_text_equals",
        "target_text_equals",
        "target_visible",
    ]
    assert conditions[0].model_dump()["expected"] == {"kind": "input", "name": "member_id"}
    assert conditions[1].model_dump()["expected"] == {
        "kind": "literal",
        "value": "Savings",
    }


def test_outputs_are_copied_only_for_verified_source_targets() -> None:
    request = _build_request()
    definition = CapabilityBuilder().build(request).definition
    assert definition.outputs == request.outputs

    request_data = request.model_dump(mode="json")
    request_data["outputs"][0]["source"]["target"] = {"value": "x.y"}
    with pytest.raises(CapabilityBuildError) as error:
        CapabilityBuilder().build(CapabilityBuildRequest.model_validate(request_data))
    assert error.value.code == "BUILD_OUTPUT_SPEC_INVALID"


def test_business_outcome_metadata_is_copied_declaratively() -> None:
    request = _build_request()
    definition = CapabilityBuilder().build(request).definition

    assert definition.business_outcomes == request.business_outcomes


def test_retry_policy_is_present_only_when_trusted_metadata_supplies_it() -> None:
    with_retry = CapabilityBuilder().build(_build_request(include_retry=True)).definition
    without_retry = CapabilityBuilder().build(_build_request(include_retry=False)).definition

    assert with_retry.steps[1].retry_policy is not None
    assert with_retry.steps[1].retry_policy.max_attempts == 3
    assert without_retry.steps[1].retry_policy is None
    assert without_retry.steps[1].postcondition is None


def test_provider_trace_and_browser_details_are_absent_from_artifact() -> None:
    serialized = CapabilityBuilder().build(_build_request()).definition.model_dump_json()

    for forbidden in (
        "gemma",
        "openai",
        "anthropic",
        "model",
        "provider",
        "observation_fingerprint",
        "gateway_outcome",
        "run_id",
        "selector",
        "iframe",
    ):
        assert forbidden not in serialized.casefold()


class TrackingValidator(CapabilityValidator):
    def __init__(self) -> None:
        self.called = False

    def validate(self, definition: CapabilityDefinition) -> ValidatedCapability:
        self.called = True
        return super().validate(definition)


class RejectingValidator(CapabilityValidator):
    def validate(self, definition: CapabilityDefinition) -> ValidatedCapability:
        raise CapabilityValidationError("rejected for test")


def test_builder_invokes_capability_validator() -> None:
    validator = TrackingValidator()

    CapabilityBuilder(validator).build(_build_request())

    assert validator.called is True


def test_validator_failure_is_normalized() -> None:
    with pytest.raises(CapabilityBuildError) as error:
        CapabilityBuilder(RejectingValidator()).build(_build_request())

    assert error.value.code == "BUILD_VALIDATION_FAILED"


def test_sensitive_sentinel_is_absent_from_artifact_request_and_error() -> None:
    sentinel = "BUILDER_PRIVATE_MEMBER_28416"
    result = _successful_result(member_id=sentinel)
    request = _build_request(result)
    artifact = CapabilityBuilder().build(request).definition.model_dump_json()

    assert sentinel not in artifact
    assert sentinel not in repr(request)


def test_equivalent_discovery_runs_build_identical_artifacts() -> None:
    first = CapabilityBuilder().build(_build_request(_successful_result())).definition
    second = CapabilityBuilder().build(
        _build_request(_successful_result("12345", "$4,382.21 USD"))
    ).definition

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_generated_semantics_match_hand_authored_reference() -> None:
    generated = CapabilityBuilder().build(_build_request()).definition
    reference = CapabilityDefinition.model_validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )

    assert generated.inputs == reference.inputs
    assert generated.outputs == reference.outputs
    assert [step.action for step in generated.steps] == [step.action for step in reference.steps]
    assert [step.precondition for step in generated.steps] == [
        step.precondition for step in reference.steps
    ]
    assert [step.postcondition for step in generated.steps] == [
        step.postcondition for step in reference.steps
    ]
    assert [step.retry_policy for step in generated.steps] == [
        step.retry_policy for step in reference.steps
    ]
    assert generated.success_conditions == reference.success_conditions
    assert generated.business_outcomes == reference.business_outcomes


def test_builder_output_round_trips_through_immutable_store(tmp_path: Path) -> None:
    built = CapabilityBuilder().build(_build_request())
    store = CapabilityStore(tmp_path / "capabilities")

    path = store.save(built)
    loaded = store.load("lookup_savings_balance", "1.0.0")

    assert loaded == built
    assert json.loads(path.read_text(encoding="utf-8")) == built.definition.model_dump(mode="json")
    with pytest.raises(CapabilityVersionAlreadyExistsError):
        store.save(built)