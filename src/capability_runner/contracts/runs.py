"""Typed run state and final results.

Run records summarize execution without embedding browser, provider, or
orchestration behavior. They describe state transitions and terminal outcomes;
runtime evidence is handled by the evidence subsystem.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RunState(ContractModel):
    run_id: str = Field(min_length=1)
    phase: Literal["queued", "running", "paused", "completed", "failed"]
    current_step: str | None = Field(default=None, min_length=1)


class RunSuccess(ContractModel):
    kind: Literal["success"] = "success"
    run_id: str = Field(min_length=1)
    outputs: dict[str, str] = Field(default_factory=dict)


class RunBusinessOutcome(ContractModel):
    kind: Literal["business_outcome"] = "business_outcome"
    run_id: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    details: str | None = Field(default=None, min_length=1)


class RunFailure(ContractModel):
    kind: Literal["failure"] = "failure"
    run_id: str = Field(min_length=1)
    step: str | None = Field(default=None, min_length=1)
    expected: str = Field(min_length=1)
    observed: str = Field(min_length=1)


type RunResult = Annotated[
    RunSuccess | RunBusinessOutcome | RunFailure,
    Field(discriminator="kind"),
]
