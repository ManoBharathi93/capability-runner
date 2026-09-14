"""Data-only contracts for bounded observation of unprofiled browser applications."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .capabilities import CapabilityDefinition
from .discovery import DiscoveryResult, GoalSpanValueSource
from .surfaces import ApplicationProfile, BrowserTargetBinding


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


ElementRef = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,15}:e[1-9][0-9]{0,4}$")]
PerceptionSource = Literal["aria", "html", "dom", "vision_region", "visual_text", "image_relation"]


class ObservationDelta(ContractModel):
    previous_generation: int = Field(ge=1)
    current_generation: int = Field(ge=1)
    added_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    changed_count: int = Field(ge=0)
    headings_changed: bool
    meaningful_text_changed: bool
    page_identity_changed: bool
    meaningful_change: bool


class BrowserScope(ContractModel):
    """Operator-owned read-only sandbox authorization, never derived from page/model text."""

    origin: str = Field(max_length=300)
    read_only_paths: tuple[str, ...] = Field(min_length=1, max_length=32)
    read_only_post_paths: tuple[str, ...] = Field(default=(), max_length=16)


class InteractiveElement(ContractModel):
    ephemeral_ref: ElementRef
    role: str = Field(max_length=40)
    accessible_name: str = Field(max_length=160)
    label: str = Field(max_length=160)
    input_type: str = Field(default="", max_length=30)
    current_value_state: Literal["empty", "set", "not_applicable"] = "not_applicable"
    visible: Literal[True] = True
    enabled: bool
    nearby_text_summary: str = Field(default="", max_length=200)
    text: str = Field(default="", max_length=256, repr=False)
    structural_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    frame_identity: str = Field(max_length=80)
    action_kind: Literal["fill", "click"] | None = None
    destination: str | None = Field(default=None, max_length=2048, repr=False)
    method: str = Field(default="", max_length=10)
    binding: BrowserTargetBinding | None = Field(default=None, repr=False)
    match_count: int = Field(ge=0)
    structural_context: str = Field(default="", max_length=200)
    perception_sources: tuple[PerceptionSource, ...] = Field(default=(), max_length=6)


class BrowserObservation(ContractModel):
    observation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    generation: int = Field(ge=1)
    page_identity: str = Field(default="", max_length=80)
    title: str = Field(max_length=160)
    origin: str = Field(max_length=300)
    path: str = Field(max_length=300)
    headings: tuple[Annotated[str, Field(max_length=160)], ...] = Field(max_length=8)
    elements: tuple[InteractiveElement, ...] = Field(max_length=64)
    truncated: bool = False
    visible_text_summary: str = Field(default="", max_length=512)
    observation_limits: dict[str, int] = Field(default_factory=dict, max_length=10)
    observation_fingerprint: str = Field(default="", max_length=64)
    change_summary: ObservationDelta | None = None

    @model_validator(mode="after")
    def validate_ref_generation(self) -> BrowserObservation:
        if any(
            int(item.ephemeral_ref.split(":", 1)[0]) != self.generation for item in self.elements
        ):
            raise ValueError("Element references must belong to the observation generation")
        if len({item.ephemeral_ref for item in self.elements}) != len(self.elements):
            raise ValueError("Duplicate element references")
        return self


class InspectDecision(ContractModel):
    kind: Literal["inspect"]


class ElementFillDecision(ContractModel):
    kind: Literal["fill"]
    observation_id: str
    element_ref: ElementRef
    input_ref: str = Field(pattern=r"^input_[1-8]$")


class ElementClickDecision(ContractModel):
    kind: Literal["click"]
    observation_id: str
    element_ref: ElementRef


class OutputEvidence(ContractModel):
    evidence_ref: ElementRef
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    parser: Literal["text", "currency_minor_units", "currency_code"] = "text"


class ElementCompleteDecision(ContractModel):
    kind: Literal["complete"]
    observation_id: str
    evidence_refs: tuple[ElementRef, ...] = Field(min_length=1, max_length=8)
    identity_refs: dict[str, ElementRef] = Field(default_factory=dict, max_length=8)
    outputs: tuple[OutputEvidence, ...] = Field(min_length=1, max_length=8)


class UnsupportedDecision(ContractModel):
    kind: Literal["fail", "unsupported"]
    reason_code: Literal[
        "UNSUPPORTED_GOAL",
        "IDENTITY_UNKNOWN",
        "SESSION_EXPIRED",
        "EVIDENCE_UNAVAILABLE",
        "POLICY_DENIED",
    ]


type BrowserDecision = Annotated[
    InspectDecision
    | ElementFillDecision
    | ElementClickDecision
    | ElementCompleteDecision
    | UnsupportedDecision,
    Field(discriminator="kind"),
]


class GoalInput(ContractModel):
    input_ref: str
    source: GoalSpanValueSource


class ApplicationIdentity(ContractModel):
    origin: str
    entry_path: str
    title: str
    fingerprint: str
    profile_version: Literal[1] = 1


class BindingEvidence(ContractModel):
    target: str
    observation_fingerprint: str
    unique_match_count: Literal[1] = 1
    re_resolved: Literal[True] = True


class CapabilityPackage(ContractModel):
    schema_version: Literal[1] = 1
    capability: CapabilityDefinition
    profile: ApplicationProfile
    identity: ApplicationIdentity
    binding_evidence: tuple[BindingEvidence, ...]
    entry_point: HttpUrl


class BrowserDiscoveryResult(ContractModel):
    result: DiscoveryResult
    observed_bindings: tuple[InteractiveElement, ...] = Field(default=(), repr=False)
    completion: ElementCompleteDecision | None = None
    input_targets: dict[str, str] = Field(default_factory=dict)
    identity: ApplicationIdentity | None = None
    verified_context: tuple[str, ...] = ()
