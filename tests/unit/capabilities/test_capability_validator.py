from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from capability_runner.capabilities.capability_validator import (
    CapabilityValidationError,
    CapabilityValidator,
)
from capability_runner.contracts.capabilities import CapabilityDefinition, FillActionTemplate
from capability_runner.contracts.surfaces import InputValueRef


def _fixture_definition() -> CapabilityDefinition:
    path = Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json")
    return CapabilityDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_development_fixture_is_structurally_valid_and_browser_agnostic() -> None:
    definition = _fixture_definition()

    validated = CapabilityValidator().validate(definition)
    fixture_text = Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json").read_text(
        encoding="utf-8"
    )

    assert validated.definition == definition
    assert "css" not in fixture_text.casefold()
    assert "xpath" not in fixture_text.casefold()
    assert "playwright" not in fixture_text.casefold()
    assert "12345" not in fixture_text


@pytest.mark.parametrize(
    ("field", "index"),
    [("inputs", 0), ("outputs", 0), ("steps", 0), ("business_outcomes", 0)],
)
def test_duplicate_names_are_rejected_by_structural_validator(field: str, index: int) -> None:
    definition = _fixture_definition()
    items = list(getattr(definition, field))
    items.append(items[index])
    invalid = definition.model_copy(update={field: tuple(items)})

    with pytest.raises(CapabilityValidationError):
        CapabilityValidator().validate(invalid)


def test_unknown_input_reference_and_missing_success_condition_are_rejected() -> None:
    definition = _fixture_definition()
    invalid = definition.model_copy(
        update={
            "steps": (
                definition.steps[0].model_copy(
                    update={
                        "action": FillActionTemplate(
                            target=definition.steps[0].action.target,
                            value=InputValueRef(kind="input", name="unknown"),
                        )
                    }
                ),
            ),
            "success_conditions": (),
        }
    )

    with pytest.raises(CapabilityValidationError) as error:
        CapabilityValidator().validate(invalid)

    assert "unknown input reference" in str(error.value)
    assert "success condition" in str(error.value)


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"schema_version": 2},
        {"steps": [{"kind": "unsupported"}]},
        {
            "outputs": [
                {
                    "name": "value",
                    "value_type": "STRING",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "regex",
                    },
                }
            ]
        },
    ],
)
def test_unsupported_schema_step_or_parser_is_rejected(invalid_payload: dict[str, object]) -> None:
    payload = _fixture_definition().model_dump(mode="python")
    payload.update(invalid_payload)

    with pytest.raises(ValidationError):
        CapabilityDefinition.model_validate(payload)
