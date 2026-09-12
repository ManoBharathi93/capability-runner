"""Safe contracts for the local P4.2 operator console."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


OperatorActionKind = Literal["fill", "click"]
OperatorControlState = Literal[
    "automation_controlled",
    "pause_requested",
    "operator_controlled",
    "resume_requested",
    "terminal",
]


class OperatorControlDescriptor(ContractModel):
    semantic_target: str = Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
    label: str = Field(min_length=1, max_length=80)
    action_kind: OperatorActionKind
    sensitive: bool = False


class OperatorInterventionStatus(ContractModel):
    intervention_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=160)
    reason_code: str = Field(min_length=1, max_length=80)
    control_state: OperatorControlState
    state_label: str = Field(min_length=1, max_length=80)
    owner_kind: Literal["automation", "operator"]
    generation: int = Field(ge=0)
    surface_kind: Literal["browser"]


class OperatorActionSubmission(ContractModel):
    semantic_target: str = Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
    action_kind: OperatorActionKind
    value: SecretStr | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def _validate_value(self) -> OperatorActionSubmission:
        if self.action_kind == "fill":
            if self.value is None or not self.value.get_secret_value():
                raise ValueError("fill actions require a non-empty value")
        elif self.value is not None:
            raise ValueError("click actions do not accept a value")
        return self


class OperatorActionResponse(ContractModel):
    executed: bool
    semantic_target: str
    action_kind: OperatorActionKind
    reason_code: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=160)


class OperatorTransitionResponse(ContractModel):
    outcome: str = Field(min_length=1, max_length=80)
    reason_code: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=160)
    control_state: OperatorControlState | None = None
    state_label: str | None = Field(default=None, min_length=1, max_length=80)
