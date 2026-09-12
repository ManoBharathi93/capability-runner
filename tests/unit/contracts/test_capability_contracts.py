from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from capability_runner.contracts.capabilities import (
    ActionStep,
    ApplicationRequirement,
    CapabilityDefinition,
    CapabilityInput,
    CapabilityOutput,
    FillActionTemplate,
    TargetTextSource,
)
from capability_runner.contracts.conditions import TargetTextEquals
from capability_runner.contracts.surfaces import InputValueRef, SemanticTargetRef


def _fixture_payload() -> dict[str, object]:
    return json.loads(
        Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_capability_definition_round_trips_with_distinct_versions() -> None:
    capability = CapabilityDefinition(
        schema_version=1,
        capability_id="lookup_savings_balance",
        capability_version="1.0.0",
        name="Lookup savings balance",
        description="Find a member savings account and return its balance.",
        application_requirement=ApplicationRequirement(
            application_family="corebank-demo",
            surface_kind="browser",
        ),
        inputs=(CapabilityInput(name="member_id", value_type="STRING", sensitive=True),),
        outputs=(
            CapabilityOutput(
                name="balance_minor_units",
                value_type="INTEGER",
                source=TargetTextSource(
                    target=SemanticTargetRef(value="member.account.balance"),
                    parser="currency_minor_units",
                ),
            ),
        ),
        steps=(
            ActionStep(
                step_id="enter_member_id",
                action=FillActionTemplate(
                    target=SemanticTargetRef(value="member.search.member_id"),
                    value=InputValueRef(kind="input", name="member_id"),
                ),
                postcondition=TargetTextEquals(
                    target=SemanticTargetRef(value="member.search.member_id"),
                    expected=InputValueRef(kind="input", name="member_id"),
                ),
            ),
        ),
        success_conditions=(
            TargetTextEquals(
                target=SemanticTargetRef(value="member.details.identity"),
                expected=InputValueRef(kind="input", name="member_id"),
            ),
        ),
    )

    assert (
        TypeAdapter(CapabilityDefinition).validate_json(capability.model_dump_json()) == capability
    )
    assert capability.schema_version == 1
    assert capability.capability_version == "1.0.0"


@pytest.mark.parametrize(
    "capability_id",
    ["../escape", "has spaces", "https://example.com", "#selector"],
)
def test_capability_identifier_rejects_paths_urls_spaces_and_selectors(capability_id: str) -> None:
    payload = _fixture_payload()
    payload["capability_id"] = capability_id

    with pytest.raises(ValidationError):
        CapabilityDefinition.model_validate(payload)


@pytest.mark.parametrize("capability_version", ["1", "v1.0.0", "1.0", "01.0.0"])
def test_capability_version_requires_deterministic_semver(capability_version: str) -> None:
    payload = _fixture_payload()
    payload["capability_version"] = capability_version

    with pytest.raises(ValidationError):
        CapabilityDefinition.model_validate(payload)


@pytest.mark.parametrize("variant", ["condition", "retry", "parser", "executable"])
def test_unsupported_or_unsafe_capability_fields_are_rejected(variant: str) -> None:
    payload = _fixture_payload()
    _apply_invalid_variant(payload, variant)

    with pytest.raises(ValidationError):
        CapabilityDefinition.model_validate(payload)


def _apply_invalid_variant(payload: dict[str, Any], variant: str) -> None:
    if variant == "condition":
        payload["success_conditions"] = [{"kind": "unknown"}]
    elif variant == "retry":
        payload["steps"][0]["retry_policy"] = {
            "kind": "wait_and_retry",
            "max_attempts": 4,
            "delay_ms": 0,
        }
    elif variant == "parser":
        payload["outputs"][0]["source"]["parser"] = "regex"
    elif variant == "executable":
        payload["executable_code"] = "import os"
    else:
        raise AssertionError(f"unknown invalid fixture variant: {variant}")
