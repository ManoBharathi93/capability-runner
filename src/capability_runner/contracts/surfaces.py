"""Typed surface abstraction contracts.

These models define the stable semantic target layer, concrete browser-target
bindings, and the profile container used by later surface adapters.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from .actions import ActionSpec
from .observations import ObservationSpec


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


SEMANTIC_TARGET_REF_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")


class SemanticTargetRef(ContractModel):
    value: str = Field(min_length=1, max_length=120)

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("semantic target ref must not have surrounding whitespace")
        if value != value.casefold():
            raise ValueError("semantic target ref must be lowercase")
        if not SEMANTIC_TARGET_REF_PATTERN.fullmatch(value):
            raise ValueError("semantic target ref must use lowercase dot-separated segments")
        return value


class InputValueRef(ContractModel):
    kind: Literal["input"] = "input"
    name: str = Field(min_length=1, max_length=80)


class LiteralValue(ContractModel):
    kind: Literal["literal"] = "literal"
    value: str = Field(min_length=1, max_length=160)


type TargetValueRef = Annotated[LiteralValue | InputValueRef, Field(discriminator="kind")]


class FrameContext(ContractModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, min_length=1, max_length=160)


class RoleLocator(ContractModel):
    kind: Literal["role"] = "role"
    role: str = Field(min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    exact: bool = False


class LabelLocator(ContractModel):
    kind: Literal["label"] = "label"
    label: str = Field(min_length=1, max_length=160)
    exact: bool = True


class TextLocator(ContractModel):
    kind: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=160)
    exact: bool = True


class CssLocator(ContractModel):
    kind: Literal["css"] = "css"
    selector: str = Field(min_length=1, max_length=240)
    structural_fallback: bool = True


type LocatorCandidate = Annotated[
    RoleLocator | LabelLocator | TextLocator | CssLocator,
    Field(discriminator="kind"),
]


class RowMatch(ContractModel):
    column: str = Field(min_length=1, max_length=80)
    value: TargetValueRef


class RowScope(ContractModel):
    table_context: LocatorCandidate | None = None
    row_match: RowMatch


class BrowserTargetBinding(ContractModel):
    semantic_target: SemanticTargetRef
    surface_kind: Literal["browser"] = "browser"
    frame: FrameContext | None = None
    row_scope: RowScope | None = None
    locator_candidates: tuple[LocatorCandidate, ...] = Field(default_factory=tuple)
    description: str | None = Field(default=None, min_length=1, max_length=160)
    review_notes: str | None = Field(default=None, min_length=1, max_length=240)
    observation_id: str | None = None
    ephemeral_ref: str | None = None

    @model_validator(mode="after")
    def _validate_locators(self) -> BrowserTargetBinding:
        if not self.locator_candidates:
            raise ValueError("locator_candidates must not be empty")
        return self


class TextOutcomeRule(ContractModel):
    text: str = Field(min_length=1, max_length=240)
    outcome: Literal["failure", "business_outcome"]
    summary: str = Field(min_length=1, max_length=160)


class ApplicationProfile(ContractModel):
    profile_id: str = Field(min_length=1, max_length=80)
    application_family: str = Field(min_length=1, max_length=80)
    variant: str = Field(min_length=1, max_length=80)
    entry_point: HttpUrl
    target_bindings: tuple[BrowserTargetBinding, ...] = Field(default_factory=tuple)
    discovery_only: bool = False
    observation_rules: tuple[TextOutcomeRule, ...] = ()

    @model_validator(mode="after")
    def _validate_target_bindings(self) -> ApplicationProfile:
        if not self.target_bindings and not self.discovery_only:
            raise ValueError("target_bindings must not be empty")

        seen: set[str] = set()
        for binding in self.target_bindings:
            target_value = binding.semantic_target.value
            if target_value in seen:
                raise ValueError("duplicate semantic target bindings are not allowed")
            seen.add(target_value)

        return self


class SurfaceSessionRef(ContractModel):
    surface_session_id: str = Field(min_length=1, max_length=80)
    surface_kind: Literal["browser"] = "browser"


class SurfaceView(ContractModel):
    surface_session: SurfaceSessionRef
    mime_type: Literal["image/png"] = "image/png"
    content: bytes = Field(min_length=1, max_length=2_000_000, repr=False)
    width: int = Field(ge=1, le=1600)
    height: int = Field(ge=1, le=1200)


SurfaceActionOutcome = Literal[
    "APPLIED",
    "TARGET_NOT_FOUND",
    "TARGET_AMBIGUOUS",
    "TARGET_NOT_ACTIONABLE",
    "SURFACE_TIMEOUT",
]


class SurfaceActionResult(ContractModel):
    outcome: SurfaceActionOutcome
    summary: str = Field(min_length=1, max_length=160)
    action: ActionSpec | None = None
    observation: ObservationSpec | None = None
    resolved_target: SemanticTargetRef | None = None


class TargetInspectionResult(ContractModel):
    outcome: Literal["VISIBLE", "NOT_VISIBLE", "UNAVAILABLE", "TARGET_AMBIGUOUS"]
    target: SemanticTargetRef
    text: str | None = Field(default=None, max_length=4096)
    summary: str = Field(min_length=1, max_length=160)


class SurfaceFailureEvidence(ContractModel):
    kind: Literal["failure"] = "failure"
    summary: str = Field(min_length=1, max_length=160)
    details: dict[str, str] = Field(default_factory=dict)


LocatorResolutionStatus = Literal["RESOLVED", "TARGET_NOT_FOUND", "TARGET_AMBIGUOUS"]


@dataclass(frozen=True, slots=True)
class LocatorResolutionOutcome:
    status: LocatorResolutionStatus
    matched_candidate_index: int | None = None


def resolve_locator_candidates(match_counts: Sequence[int]) -> LocatorResolutionOutcome:
    if not match_counts:
        return LocatorResolutionOutcome(status="TARGET_NOT_FOUND")

    for index, count in enumerate(match_counts):
        if count < 0:
            raise ValueError("match_counts must not contain negative values")
        if count == 1:
            return LocatorResolutionOutcome(status="RESOLVED", matched_candidate_index=index)
        if count > 1:
            return LocatorResolutionOutcome(
                status="TARGET_AMBIGUOUS",
                matched_candidate_index=index,
            )

    return LocatorResolutionOutcome(status="TARGET_NOT_FOUND")
