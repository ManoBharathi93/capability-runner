from __future__ import annotations

import json
from typing import cast

import pytest
from pydantic import HttpUrl, TypeAdapter, ValidationError

from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    FrameContext,
    InputValueRef,
    LabelLocator,
    LiteralValue,
    LocatorCandidate,
    LocatorResolutionOutcome,
    RoleLocator,
    RowMatch,
    RowScope,
    SemanticTargetRef,
    SurfaceActionResult,
    SurfaceFailureEvidence,
    SurfaceSessionRef,
    SurfaceView,
    TextLocator,
    resolve_locator_candidates,
)


def _browser_binding() -> BrowserTargetBinding:
    return BrowserTargetBinding(
        semantic_target=SemanticTargetRef(value="member.search.submit"),
        frame=FrameContext(name="work-area"),
        locator_candidates=(
            RoleLocator(kind="role", role="button", name="Search", exact=True),
            TextLocator(kind="text", text="Search", exact=True),
        ),
        description="Search submit button",
    )


def test_valid_semantic_target_ids_are_accepted() -> None:
    ref = SemanticTargetRef(value="member.accounts.savings")

    assert ref.value == "member.accounts.savings"
    assert TypeAdapter(SemanticTargetRef).validate_json(ref.model_dump_json()) == ref


@pytest.mark.parametrize(
    "invalid_value",
    [
        "",
        "member search submit",
        "HTTPS://example.com",
        "https://example.com/path",
        "member.results../open",
        "member.results.open/child",
        "member.results.open?x=1",
        "member.results.open#anchor",
        "member.results.open:nth-child(2)",
        "../member.results.open",
    ],
)
def test_invalid_semantic_target_ids_are_rejected(invalid_value: str) -> None:
    with pytest.raises(ValidationError):
        SemanticTargetRef(value=invalid_value)


def test_browser_binding_serializes_and_round_trips() -> None:
    binding = _browser_binding()

    round_trip = TypeAdapter(BrowserTargetBinding).validate_json(binding.model_dump_json())

    assert round_trip == binding
    assert round_trip.locator_candidates[0].kind == "role"


def test_locator_candidates_use_explicit_discriminators() -> None:
    candidate = cast(
        LabelLocator,
        TypeAdapter(LocatorCandidate).validate_json(
        json.dumps({"kind": "label", "label": "Member ID", "exact": True})
        ),
    )

    assert isinstance(candidate, LabelLocator)


def test_unknown_locator_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(LocatorCandidate).validate_json(
            json.dumps({"kind": "xpath", "selector": "//div"})
        )


def test_locator_candidate_order_is_preserved() -> None:
    binding = BrowserTargetBinding(
        semantic_target=SemanticTargetRef(value="member.search.member_id"),
        frame=FrameContext(name="work-area"),
        locator_candidates=(
            CssLocator(kind="css", selector="input[name='member_id']", structural_fallback=True),
            LabelLocator(kind="label", label="Member ID", exact=True),
        ),
    )

    assert [candidate.kind for candidate in binding.locator_candidates] == ["css", "label"]


def test_css_fallback_is_structural_and_representable() -> None:
    candidate = CssLocator(
        kind="css",
        selector="table.search-results tr:nth-child(1) a.open-link",
        structural_fallback=True,
    )

    assert candidate.structural_fallback is True
    assert candidate.kind == "css"


def test_frame_context_is_explicit() -> None:
    binding = _browser_binding()

    assert binding.frame == FrameContext(name="work-area")
    assert binding.frame is not None


def test_input_value_ref_parameterization_is_supported() -> None:
    row_match = RowMatch(column="Member ID", value=InputValueRef(kind="input", name="member_id"))

    assert row_match.value.kind == "input"
    assert row_match.value.name == "member_id"


def test_literal_value_is_distinct_from_input_value_ref() -> None:
    literal = LiteralValue(kind="literal", value="12345")
    input_ref = InputValueRef(kind="input", name="member_id")

    assert literal != input_ref
    assert literal.kind == "literal"
    assert input_ref.kind == "input"


def test_row_scoped_repeated_open_link_target_is_representable() -> None:
    binding = BrowserTargetBinding(
        semantic_target=SemanticTargetRef(value="member.results.open"),
        frame=FrameContext(name="work-area"),
        row_scope=RowScope(
            table_context=RoleLocator(kind="role", role="table", name="Search Results", exact=True),
            row_match=RowMatch(
                column="Member ID",
                value=InputValueRef(kind="input", name="member_id"),
            ),
        ),
        locator_candidates=(
            RoleLocator(kind="role", role="link", name="Open", exact=True),
            TextLocator(kind="text", text="Open", exact=True),
        ),
    )

    assert binding.row_scope is not None
    assert binding.row_scope.row_match.column == "Member ID"
    assert binding.row_scope.row_match.value.kind == "input"


def test_empty_locator_candidate_list_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BrowserTargetBinding(
            semantic_target=SemanticTargetRef(value="member.search.submit"),
            frame=FrameContext(name="work-area"),
            locator_candidates=(),
        )


def test_duplicate_semantic_target_bindings_are_rejected() -> None:
    binding = _browser_binding()

    with pytest.raises(ValidationError):
        ApplicationProfile(
            profile_id="bank-demo",
            application_family="banking",
            variant="legacy-ui",
            entry_point=TypeAdapter(HttpUrl).validate_python("http://127.0.0.1:5000/workspace"),
            target_bindings=(binding, binding),
        )


def test_application_profile_round_trips() -> None:
    profile = ApplicationProfile(
        profile_id="bank-demo",
        application_family="banking",
        variant="legacy-ui",
        entry_point=TypeAdapter(HttpUrl).validate_python("http://127.0.0.1:5000/workspace"),
        target_bindings=(_browser_binding(),),
    )

    assert TypeAdapter(ApplicationProfile).validate_json(profile.model_dump_json()) == profile


def test_binding_cannot_use_unsupported_surface_kind() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(BrowserTargetBinding).validate_json(
            json.dumps(
                {
                    "semantic_target": {"value": "member.search.submit"},
                    "surface_kind": "desktop",
                    "frame": {"name": "work-area"},
                    "locator_candidates": [
                        {"kind": "role", "role": "button", "name": "Search", "exact": True}
                    ],
                }
            )
        )


def test_locator_fallback_semantics_are_explicit() -> None:
    assert resolve_locator_candidates([0, 0, 1]) == LocatorResolutionOutcome(
        status="RESOLVED",
        matched_candidate_index=2,
    )
    assert resolve_locator_candidates([0, 2, 1]).status == "TARGET_AMBIGUOUS"
    assert resolve_locator_candidates([0, 0]).status == "TARGET_NOT_FOUND"


def test_surface_evidence_result_is_typed() -> None:
    result = SurfaceActionResult(
        outcome="TARGET_NOT_FOUND",
        summary="Could not resolve the member search submit control.",
    )
    evidence = SurfaceFailureEvidence(kind="failure", summary="Search timed out")

    assert result.outcome == "TARGET_NOT_FOUND"
    assert evidence.kind == "failure"


def test_surface_view_is_bounded_and_does_not_repr_content() -> None:
    session = SurfaceSessionRef(surface_session_id="surface-1")
    view = SurfaceView(
        surface_session=session,
        content=b"\x89PNG\r\n\x1a\n",
        width=1280,
        height=720,
    )

    assert view.surface_session == session
    assert view.mime_type == "image/png"
    assert "PNG" not in repr(view)

    with pytest.raises(ValidationError):
        SurfaceView(
            surface_session=session,
            content=b"x" * 2_000_001,
            width=1280,
            height=720,
        )
