from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from capability_runner.capabilities.binding_compiler import compile_binding
from capability_runner.contracts.browser_discovery import (
    BrowserObservation,
    BrowserScope,
    InteractiveElement,
)
from capability_runner.contracts.requests import DiscoveryRequest
from capability_runner.contracts.surfaces import (
    BrowserTargetBinding,
    RoleLocator,
    SemanticTargetRef,
)
from capability_runner.discovery.browser_discovery import DECISIONS, goal_inputs, present_browser
from capability_runner.interaction.policy_guard import observed_action_allowed
from capability_runner.surfaces.browser_observation import (
    bound_observation,
    method_allowed,
    observation_delta,
    within_scope,
)


def element(**changes: object) -> InteractiveElement:
    value: dict[str, object] = {
        "ephemeral_ref": "1:e1",
        "role": "button",
        "accessible_name": "Search",
        "label": "Search",
        "enabled": True,
        "structural_fingerprint": "a" * 64,
        "frame_identity": "main",
        "action_kind": "click",
        "destination": "http://127.0.0.1:8000/sandbox/find",
        "method": "GET",
        "match_count": 1,
        "binding": BrowserTargetBinding(
            semantic_target=SemanticTargetRef(value="page.button.search"),
            locator_candidates=(RoleLocator(role="button", name="Search", exact=True),),
        ),
    }
    value.update(changes)
    return InteractiveElement.model_validate(value)


@pytest.mark.parametrize(
    "goal", ["Find record 12345.", "What's in record 12345?", "Delete every record."]
)
def test_arbitrary_goal_is_validated_as_data(goal: str) -> None:
    request = DiscoveryRequest.model_validate(
        {"goal": goal, "target": {"kind": "url", "url": "http://localhost/"}}
    )
    assert request.goal == goal


@pytest.mark.parametrize("goal", ["", "   ", "x" * 4001])
def test_empty_or_oversized_goal_is_rejected(goal: str) -> None:
    with pytest.raises(ValidationError):
        DiscoveryRequest.model_validate(
            {"goal": goal, "target": {"kind": "url", "url": "http://localhost/"}}
        )


@pytest.mark.parametrize(
    "field", ["css", "xpath", "javascript", "shell", "playwright", "confidence"]
)
def test_model_cannot_supply_executable_fields_or_confidence(field: str) -> None:
    with pytest.raises(ValidationError):
        DECISIONS.validate_python(
            {"kind": "click", "observation_id": "a" * 32, "element_ref": "1:e1", field: "untrusted"}
        )


def test_prompt_is_bounded_and_masks_runtime_identifiers() -> None:
    goal = "Find record 67890."
    observation = BrowserObservation(
        observation_id="a" * 32,
        generation=1,
        title="Records",
        origin="http://localhost",
        path="/",
        headings=(),
        elements=tuple(
            element(
                ephemeral_ref=f"1:e{i}",
                text="67890 12345 bearer private-token",
                nearby_text_summary="x" * 200,
            )
            for i in range(1, 65)
        ),
    )
    request = present_browser(goal, observation, goal_inputs(goal), [], None)
    payload = request.messages[-1].content
    assert len(payload) <= 16000
    assert "67890" not in payload and "12345" not in payload and "private-token" not in payload
    assert "<input_1>" in payload
    assert "locator_candidates" not in payload
    assert len(json.loads(payload)["elements"]) <= 64


def test_goal_page_and_model_cannot_grant_action_authority() -> None:
    scope = BrowserScope(origin="http://127.0.0.1:8000", read_only_paths=("/sandbox",))
    assert observed_action_allowed(element(), scope)
    assert not observed_action_allowed(element(accessible_name="Delete Account"), scope)
    assert not observed_action_allowed(element(method="POST"), scope)
    assert not observed_action_allowed(element(method=""), scope)
    assert not observed_action_allowed(element(destination="https://example.com/"), scope)
    assert not observed_action_allowed(element(match_count=2), scope)
    assert not observed_action_allowed(element(enabled=False), scope)


@pytest.mark.parametrize(
    "suffix",
    [
        "/sandbox/../delete",
        "/sandbox/%2e%2e/delete",
        "/sandbox/%252e%252e/delete",
        "/sandbox-other",
    ],
)
def test_route_prefix_cannot_escape_authorized_scope(suffix: str) -> None:
    scope = BrowserScope(origin="http://127.0.0.1:8000", read_only_paths=("/sandbox",))
    assert not within_scope(scope.origin + suffix, scope)
    assert not method_allowed("POST", scope.origin + "/sandbox/find", scope)


@pytest.mark.parametrize("count", [0, 2])
def test_compiler_rejects_unresolved_or_ambiguous_bindings(count: int) -> None:
    with pytest.raises(ValueError, match="TARGET_AMBIGUOUS"):
        compile_binding(element(match_count=count), {})


def test_binding_naming_is_deterministic_and_separate_from_ephemeral_refs() -> None:
    first = compile_binding(element(), {})
    second = compile_binding(element(ephemeral_ref="1:e95"), {})
    assert first == second
    assert first.semantic_target.value.endswith(".search")
    assert first.ephemeral_ref is None and first.observation_id is None


@pytest.mark.parametrize("ref", ["e1", "0:e1", "1:e0", "1:e-1", "1:e1:extra", "99", "x:e1", ""])
def test_decision_parser_requires_well_formed_generation(ref: str) -> None:
    with pytest.raises(ValidationError):
        DECISIONS.validate_python(
            {
                "kind": "click",
                "observation_id": "a" * 32,
                "element_ref": ref,
            }
        )


def test_snapshot_rejects_mixed_generations_and_duplicate_refs() -> None:
    for elements in [(element(ephemeral_ref="2:e1"),), (element(), element())]:
        with pytest.raises(ValidationError):
            BrowserObservation(
                observation_id="a" * 32,
                generation=1,
                title="Records",
                origin="http://localhost",
                path="/",
                headings=(),
                elements=elements,
            )


def test_stable_delta_ignores_generation_clock_and_uuid_but_detects_result_and_enabled_state() -> (
    None
):
    def snapshot(generation: int, text: str, *, enabled: bool = True) -> BrowserObservation:
        return bound_observation(
            BrowserObservation(
                observation_id=str(generation) * 32,
                generation=generation,
                title="Records",
                origin="http://localhost",
                path="/",
                headings=("Result",),
                elements=(element(ephemeral_ref=f"{generation}:e1", text=text, enabled=enabled),),
            )
        )

    first = snapshot(1, "12:10:15 8ef1f574-7587-4c86-901e-3433d077a1cf Balance 4382.21")
    second = snapshot(2, "12:10:16 83630dfe-16e8-40fd-b625-cc45a87fc02b Balance 4382.21")
    assert first.observation_fingerprint == second.observation_fingerprint
    assert not observation_delta(first, second).meaningful_change
    changed = snapshot(3, "12:10:17 Balance 987.65", enabled=False)
    delta = observation_delta(second, changed)
    assert delta.changed_count == 1 and delta.meaningful_text_changed
    assert delta.meaningful_change
    assert first.observation_fingerprint != changed.observation_fingerprint


def test_presenter_masks_all_page_context_without_corrupting_ref_generation() -> None:
    goal = "Find record 67890."
    observation = BrowserObservation(
        observation_id="a" * 32,
        generation=12345,
        title="Record 67890",
        origin="http://localhost",
        path="/",
        headings=("bearer headingCanary",),
        visible_text_summary="sk-summaryCanary",
        elements=(element(ephemeral_ref="12345:e1", structural_context="Record 67890"),),
    )
    request = present_browser(
        goal,
        observation,
        goal_inputs(goal),
        [
            {"label": "sk-historyCanary", "kind": "inspect"},
        ],
        None,
    )
    serialized = request.messages[-1].content
    assert "Canary" not in serialized and "67890" not in serialized
    payload = json.loads(serialized)
    assert payload["generation"] == 12345
    assert payload["elements"][0]["ref"] == "12345:e1"
    assert payload["elements"][0]["context"] == "Record <input_1>"


def test_summary_truncation_is_reported_even_below_total_text_budget() -> None:
    observation = BrowserObservation(
        observation_id="a" * 32,
        generation=1,
        title="Records",
        origin="http://localhost",
        path="/",
        headings=(),
        elements=tuple(element(ephemeral_ref=f"1:e{i}", text="a" * 200) for i in range(1, 4)),
    )
    bounded = bound_observation(observation)
    assert len(bounded.visible_text_summary) == 512
    assert len(bounded.elements) == 3
    assert bounded.truncated
