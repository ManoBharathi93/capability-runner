"""Typed, serializable capability definition contracts."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .conditions import ConditionSpec
from .surfaces import SemanticTargetRef, TargetValueRef

CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


ValueType = Literal["STRING", "INTEGER", "BOOLEAN", "DECIMAL", "CURRENCY_CODE"]
OutputParser = Literal["currency_minor_units", "currency_code", "text"]


class ApplicationRequirement(ContractModel):
    application_family: str = Field(min_length=1, max_length=80)
    surface_kind: Literal["browser"]
    compatible_variant: str | None = Field(default=None, min_length=1, max_length=80)


class CapabilityInput(ContractModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    value_type: ValueType
    required: bool = True
    sensitive: bool = False
    min_length: int | None = Field(default=None, ge=0, le=4096)
    max_length: int | None = Field(default=None, ge=1, le=4096)
    pattern: str | None = Field(default=None, min_length=1, max_length=240)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, value: str | None) -> str | None:
        if value is not None:
            re.compile(value)
        return value


class TargetTextSource(ContractModel):
    kind: Literal["target_text"] = "target_text"
    target: SemanticTargetRef
    parser: OutputParser


class CapabilityOutput(ContractModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    value_type: ValueType
    source: TargetTextSource


class FillActionTemplate(ContractModel):
    kind: Literal["fill"] = "fill"
    target: SemanticTargetRef
    value: TargetValueRef


class ClickActionTemplate(ContractModel):
    kind: Literal["click"] = "click"
    target: SemanticTargetRef


type CapabilityActionTemplate = Annotated[
    FillActionTemplate | ClickActionTemplate,
    Field(discriminator="kind"),
]


class RetryPolicy(ContractModel):
    kind: Literal["wait_and_retry"] = "wait_and_retry"
    max_attempts: int = Field(ge=1, le=3)
    delay_ms: int = Field(ge=0, le=60_000)


class ActionStep(ContractModel):
    kind: Literal["action"] = "action"
    step_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    action: CapabilityActionTemplate
    precondition: ConditionSpec | None = None
    postcondition: ConditionSpec | None = None
    retry_policy: RetryPolicy | None = None


type CapabilityStep = Annotated[ActionStep, Field(discriminator="kind")]


class BusinessOutcomeRule(ContractModel):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    description: str = Field(min_length=1, max_length=240)
    conditions: tuple[ConditionSpec, ...] = Field(min_length=1, max_length=8)


class CapabilityDefinition(ContractModel):
    schema_version: Literal[1] = 1
    capability_id: str = Field(min_length=1, max_length=80)
    capability_version: str = Field(min_length=5, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    application_requirement: ApplicationRequirement
    inputs: tuple[CapabilityInput, ...] = Field(default_factory=tuple, max_length=32)
    outputs: tuple[CapabilityOutput, ...] = Field(default_factory=tuple, max_length=32)
    steps: tuple[CapabilityStep, ...] = Field(default_factory=tuple, max_length=64)
    success_conditions: tuple[ConditionSpec, ...] = Field(default_factory=tuple, max_length=16)
    business_outcomes: tuple[BusinessOutcomeRule, ...] = Field(default_factory=tuple, max_length=16)

    @field_validator("capability_id")
    @classmethod
    def validate_capability_id(cls, value: str) -> str:
        if not CAPABILITY_ID_PATTERN.fullmatch(value):
            raise ValueError("capability_id must use lowercase underscore-separated words")
        return value

    @field_validator("capability_version")
    @classmethod
    def validate_capability_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("capability_version must be a semantic version")
        return value
