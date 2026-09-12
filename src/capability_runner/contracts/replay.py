"""Typed deterministic replay invocation and outcome contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


ReplayOutcome = Literal["SUCCESS", "BUSINESS_OUTCOME", "FAILURE"]


class ReplayCheckpoint(ContractModel):
    capability_id: str = Field(min_length=1, max_length=80)
    capability_version: str = Field(min_length=1, max_length=40)
    blocked_step_id: str = Field(min_length=1, max_length=80)
    blocked_step_index: int = Field(ge=0)
    reason_code: Literal["APPROVAL_REQUIRED"] = "APPROVAL_REQUIRED"
    action_effect_state: Literal["NOT_EXECUTED"] = "NOT_EXECUTED"
    suspended_generation: int = Field(ge=0)


class ReplayResult(ContractModel):
    outcome: ReplayOutcome
    run_id: str = Field(min_length=1, max_length=128)
    outputs: dict[str, str | int] = Field(default_factory=dict)
    business_outcome_code: str | None = Field(default=None, min_length=1, max_length=80)
    reason_code: str | None = Field(default=None, min_length=1, max_length=80)
    step_id: str | None = Field(default=None, min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=160)
    steps_attempted: int = Field(ge=0)
    checkpoint: ReplayCheckpoint | None = None
