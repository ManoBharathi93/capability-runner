"""Data-only contracts for bounded observation of unprofiled browser applications."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .capabilities import CapabilityDefinition
from .discovery import DiscoveryResult, GoalSpanValueSource
from .surfaces import ApplicationProfile, BrowserTargetBinding


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BrowserScope(ContractModel):
    """Operator-owned read-only sandbox authorization, never derived from page/model text."""

    origin: str = Field(max_length=300)
    read_only_paths: tuple[str, ...] = Field(min_length=1, max_length=32)
    read_only_post_paths: tuple[str, ...] = Field(default=(), max_length=16)


class InteractiveElement(ContractModel):
    ephemeral_ref: str = Field(pattern=r"^e[0-9]+$")
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


class BrowserObservation(ContractModel):
    observation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    title: str = Field(max_length=160)
    origin: str = Field(max_length=300)
    path: str = Field(max_length=300)
    headings: tuple[str, ...] = Field(max_length=8)
    elements: tuple[InteractiveElement, ...] = Field(max_length=64)
    truncated: bool = False


class InspectDecision(ContractModel):
    kind: Literal["inspect"]


class ElementFillDecision(ContractModel):
    kind: Literal["fill"]
    observation_id: str
    element_ref: str = Field(pattern=r"^e[0-9]+$")
    input_ref: str = Field(pattern=r"^input_[1-8]$")


class ElementClickDecision(ContractModel):
    kind: Literal["click"]
    observation_id: str
    element_ref: str = Field(pattern=r"^e[0-9]+$")


class OutputEvidence(ContractModel):
    evidence_ref: str = Field(pattern=r"^e[0-9]+$")
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    parser: Literal["text", "currency_minor_units", "currency_code"] = "text"


class ElementCompleteDecision(ContractModel):
    kind: Literal["complete"]
    observation_id: str
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=8)
    identity_refs: dict[str, str] = Field(default_factory=dict, max_length=8)
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
