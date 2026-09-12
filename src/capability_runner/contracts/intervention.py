"""Immutable contracts for same-session human intervention."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .sessions import SessionState
from .surfaces import SurfaceSessionRef


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InterventionRequest(ContractModel):
    intervention_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    control_session_id: str = Field(min_length=1, max_length=128)
    surface_session: SurfaceSessionRef
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    summary: str = Field(min_length=1, max_length=160)


class InterventionRecord(ContractModel):
    intervention_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    control_session_id: str = Field(min_length=1, max_length=128)
    surface_session: SurfaceSessionRef
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    summary: str = Field(min_length=1, max_length=160)
    requested_generation: int = Field(ge=0)


class ResumeValidationResult(ContractModel):
    outcome: Literal["VALID", "INVALID"]
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    summary: str = Field(min_length=1, max_length=160)


InterventionOutcome = Literal[
    "INTERVENTION_REQUESTED",
    "WAITING_FOR_QUIESCENCE",
    "OPERATOR_CONTROLLED",
    "RESUME_VALIDATION_REQUIRED",
    "RESUMED",
    "VALIDATION_FAILED",
    "SESSION_STOPPED",
    "STALE_GENERATION",
    "INVALID_STATE",
]


class InterventionResult(ContractModel):
    outcome: InterventionOutcome
    record: InterventionRecord | None = None
    session_state: SessionState | None = None
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    summary: str = Field(min_length=1, max_length=160)
