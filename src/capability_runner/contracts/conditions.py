"""Declarative condition contracts for future capability evaluation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .surfaces import SemanticTargetRef, TargetValueRef


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TargetVisible(ContractModel):
    kind: Literal["target_visible"] = "target_visible"
    target: SemanticTargetRef


class TargetTextEquals(ContractModel):
    kind: Literal["target_text_equals"] = "target_text_equals"
    target: SemanticTargetRef
    expected: TargetValueRef


class TargetTextContains(ContractModel):
    kind: Literal["target_text_contains"] = "target_text_contains"
    target: SemanticTargetRef
    expected: TargetValueRef


type ConditionSpec = Annotated[
    TargetVisible | TargetTextEquals | TargetTextContains,
    Field(discriminator="kind"),
]
