"""Strict contracts at the untrusted discovery-model boundary."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from .surfaces import SEMANTIC_TARGET_REF_PATTERN


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DiscoveryFillAction(ContractModel):
    kind: Literal["fill"] = "fill"
    target: str = Field(min_length=1, max_length=120, pattern=SEMANTIC_TARGET_REF_PATTERN.pattern)
    value: SecretStr


class DiscoveryClickAction(ContractModel):
    kind: Literal["click"] = "click"
    target: str = Field(min_length=1, max_length=120, pattern=SEMANTIC_TARGET_REF_PATTERN.pattern)


type DiscoveryAction = Annotated[
    DiscoveryFillAction | DiscoveryClickAction,
    Field(discriminator="kind"),
]


class ActDecision(ContractModel):
    kind: Literal["ACT"] = "ACT"
    action: DiscoveryAction


class CompletionEvidence(ContractModel):
    target: str = Field(min_length=1, max_length=120, pattern=SEMANTIC_TARGET_REF_PATTERN.pattern)
    observed_text: SecretStr


class CompleteDecision(ContractModel):
    kind: Literal["COMPLETE"] = "COMPLETE"
    evidence: tuple[CompletionEvidence, ...] = Field(min_length=1, max_length=8)


class RequestInterventionDecision(ContractModel):
    kind: Literal["REQUEST_INTERVENTION"] = "REQUEST_INTERVENTION"
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")


class FailDecision(ContractModel):
    kind: Literal["FAIL"] = "FAIL"
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")


type DiscoveryDecision = Annotated[
    ActDecision | CompleteDecision | RequestInterventionDecision | FailDecision,
    Field(discriminator="kind"),
]


class GoalSpanValueSource(ContractModel):
    kind: Literal["goal_span"] = "goal_span"
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_span(self) -> GoalSpanValueSource:
        if self.end <= self.start:
            raise ValueError("goal span end must be greater than start")
        return self


class VerifiedCompletionEvidence(ContractModel):
    target: str = Field(min_length=1, max_length=120, pattern=SEMANTIC_TARGET_REF_PATTERN.pattern)
    text_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    goal_span_action_target: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        pattern=SEMANTIC_TARGET_REF_PATTERN.pattern,
    )


class DiscoveryTraceEntry(ContractModel):
    turn: int = Field(ge=1, le=12)
    decision_kind: Literal["ACT", "COMPLETE", "REQUEST_INTERVENTION", "FAIL", "INVALID"]
    action_kind: Literal["fill", "click"] | None = None
    semantic_target: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        pattern=SEMANTIC_TARGET_REF_PATTERN.pattern,
    )
    value_source: GoalSpanValueSource | None = None
    gateway_outcome: Literal["EXECUTED", "DENIED", "APPROVAL_REQUIRED", "FAILED"] | None = None
    observation_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    outcome: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")

    @model_validator(mode="after")
    def validate_action_fields(self) -> DiscoveryTraceEntry:
        has_action = self.action_kind is not None or self.semantic_target is not None
        if self.decision_kind == "ACT" and not (
            self.action_kind is not None and self.semantic_target is not None
        ):
            raise ValueError("ACT trace entries require action kind and semantic target")
        if self.decision_kind != "ACT" and has_action:
            raise ValueError("non-ACT trace entries must not carry action fields")
        if self.decision_kind != "ACT" and (
            self.value_source is not None or self.gateway_outcome is not None
        ):
            raise ValueError("non-ACT trace entries must not carry action execution fields")
        if self.action_kind != "fill" and self.value_source is not None:
            raise ValueError("only fill trace entries may carry a value source")
        return self


DiscoveryOutcome = Literal["SUCCESS", "INTERVENTION_REQUIRED", "FAILED"]


class DiscoveryResult(ContractModel):
    outcome: DiscoveryOutcome
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    turns: int = Field(ge=0, le=12)
    actions: int = Field(ge=0, le=8)
    verified_targets: tuple[str, ...] = Field(default_factory=tuple, max_length=8)
    completion_evidence: tuple[VerifiedCompletionEvidence, ...] = Field(
        default_factory=tuple,
        max_length=8,
    )
    trace: tuple[DiscoveryTraceEntry, ...] = Field(default_factory=tuple, max_length=12)
