"""Trusted authoring inputs for deterministic capability compilation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .capabilities import (
    ApplicationRequirement,
    BusinessOutcomeRule,
    CapabilityOutput,
    RetryPolicy,
)
from .conditions import ConditionSpec
from .discovery import DiscoveryResult
from .surfaces import SemanticTargetRef


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InputSensitivityDeclaration(ContractModel):
    action_target: SemanticTargetRef
    sensitive: bool


class InputEqualitySuccessTemplate(ContractModel):
    kind: Literal["input_equals"] = "input_equals"
    target: SemanticTargetRef
    input_action_target: SemanticTargetRef


class LiteralEqualitySuccessTemplate(ContractModel):
    kind: Literal["literal_equals"] = "literal_equals"
    target: SemanticTargetRef
    expected: str = Field(min_length=1, max_length=160)


class VisibleSuccessTemplate(ContractModel):
    kind: Literal["target_visible"] = "target_visible"
    target: SemanticTargetRef


type SuccessTemplate = Annotated[
    InputEqualitySuccessTemplate | LiteralEqualitySuccessTemplate | VisibleSuccessTemplate,
    Field(discriminator="kind"),
]


class StepReplayMetadata(ContractModel):
    action_kind: Literal["fill", "click"]
    target: SemanticTargetRef
    occurrence: int = Field(default=1, ge=1, le=64)
    precondition: ConditionSpec | None = None
    postcondition: ConditionSpec | None = None
    retry_policy: RetryPolicy | None = None


class CapabilityBuildRequest(ContractModel):
    capability_id: str = Field(min_length=1, max_length=80)
    capability_version: str = Field(min_length=5, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    discovery_result: DiscoveryResult
    application_requirement: ApplicationRequirement
    input_sensitivity: tuple[InputSensitivityDeclaration, ...] = Field(
        default_factory=tuple,
        max_length=32,
    )
    success_templates: tuple[SuccessTemplate, ...] = Field(
        default_factory=tuple,
        max_length=16,
    )
    outputs: tuple[CapabilityOutput, ...] = Field(default_factory=tuple, max_length=32)
    business_outcomes: tuple[BusinessOutcomeRule, ...] = Field(
        default_factory=tuple,
        max_length=16,
    )
    step_metadata: tuple[StepReplayMetadata, ...] = Field(default_factory=tuple, max_length=64)
