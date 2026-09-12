from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from capability_runner.contracts.discovery import (
    ActDecision,
    CompleteDecision,
    DiscoveryDecision,
    DiscoveryFillAction,
)

DECISION_ADAPTER: TypeAdapter[DiscoveryDecision] = TypeAdapter(DiscoveryDecision)


def test_fill_decision_parses_and_redacts_value() -> None:
    raw = json.dumps(
        {
            "kind": "ACT",
            "action": {
                "kind": "fill",
                "target": "member.search.member_id",
                "value": "MEMBER_PRIVATE_74291",
            },
        }
    )

    decision = DECISION_ADAPTER.validate_json(raw)

    assert isinstance(decision, ActDecision)
    assert isinstance(decision.action, DiscoveryFillAction)
    assert decision.action.value.get_secret_value() == "MEMBER_PRIVATE_74291"
    assert "MEMBER_PRIVATE_74291" not in repr(decision)
    assert "MEMBER_PRIVATE_74291" not in decision.model_dump_json()


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "ACT", "action": {"kind": "navigate", "url": "https://example.com"}},
        {"kind": "ACT", "action": {"kind": "click", "target": "#search-button"}},
        {
            "kind": "ACT",
            "action": {
                "kind": "click",
                "target": "member.search.submit",
                "selector": "#search-button",
            },
        },
        {"kind": "WAIT", "seconds": 1},
    ],
)
def test_decision_rejects_unsupported_actions_selectors_and_kinds(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        DECISION_ADAPTER.validate_python(payload)


def test_complete_decision_requires_bounded_semantic_evidence() -> None:
    decision = DECISION_ADAPTER.validate_python(
        {
            "kind": "COMPLETE",
            "evidence": [
                {"target": "member.details.identity", "observed_text": "67890"},
                {"target": "member.account.balance", "observed_text": "$987.65 USD"},
            ],
        }
    )

    assert isinstance(decision, CompleteDecision)
    assert len(decision.evidence) == 2
    assert "67890" not in decision.model_dump_json()


def test_decisions_are_immutable_and_reject_extra_fields() -> None:
    decision = DECISION_ADAPTER.validate_python(
        {
            "kind": "ACT",
            "action": {"kind": "click", "target": "member.search.submit"},
        }
    )

    with pytest.raises(ValidationError):
        DECISION_ADAPTER.validate_python(
            {
                "kind": "FAIL",
                "reason_code": "UNSUPPORTED_STATE",
                "details": "untrusted raw text",
            }
        )
    with pytest.raises(ValidationError):
        decision.kind = "FAIL"  # type: ignore[misc]