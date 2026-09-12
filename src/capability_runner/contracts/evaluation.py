"""Pure semantic target snapshots consumed by deterministic evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .surfaces import SemanticTargetRef


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


TargetObservationState = Literal["VISIBLE", "NOT_VISIBLE", "UNAVAILABLE"]


class TargetObservation(ContractModel):
    target: SemanticTargetRef
    state: TargetObservationState
    text: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def validate_text_state(self) -> TargetObservation:
        if self.state != "VISIBLE" and self.text is not None:
            raise ValueError("only visible targets may include text")
        return self


class EvaluationSnapshot(ContractModel):
    observed_targets: tuple[TargetObservation, ...] = Field(max_length=256)

    @model_validator(mode="after")
    def validate_unique_targets(self) -> EvaluationSnapshot:
        target_values = [item.target.value for item in self.observed_targets]
        if len(target_values) != len(set(target_values)):
            raise ValueError("evaluation snapshot must not repeat semantic targets")
        return self
