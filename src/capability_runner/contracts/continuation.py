"""Safe public results for replay continuation orchestration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .intervention import InterventionRecord
from .replay import ReplayResult


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


ContinuationOutcome = Literal[
    "INTERVENTION_REQUIRED",
    "SUCCESS",
    "BUSINESS_OUTCOME",
    "FAILURE",
    "VALIDATION_FAILED",
    "SESSION_STOPPED",
    "CONTINUATION_ALREADY_CONSUMED",
    "INVALID_CONTINUATION",
]


class ReplayContinuationResult(ContractModel):
    outcome: ContinuationOutcome
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    summary: str = Field(min_length=1, max_length=160)
    intervention: InterventionRecord | None = None
    replay_result: ReplayResult | None = None
    generation_before: int | None = Field(default=None, ge=0)
    generation_after: int | None = Field(default=None, ge=0)
