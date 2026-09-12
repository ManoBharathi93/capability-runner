"""Typed Action Gateway request and result contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .actions import ActionSpec
from .surfaces import ApplicationProfile, SemanticTargetRef, SurfaceActionOutcome, SurfaceSessionRef


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GatewayActionRequest(ContractModel):
    action_id: str = Field(min_length=1, max_length=128)
    semantic_target: SemanticTargetRef
    action: ActionSpec
    step_id: str | None = Field(default=None, min_length=1, max_length=128)


class GatewayExecutionContext(ContractModel):
    run_id: str = Field(min_length=1, max_length=128)
    control_session_id: str = Field(min_length=1, max_length=128)
    expected_generation: int = Field(ge=0)
    surface_session: SurfaceSessionRef
    profile: ApplicationProfile


GatewayOutcome = Literal["EXECUTED", "DENIED", "APPROVAL_REQUIRED", "FAILED"]


class GatewayResult(ContractModel):
    outcome: GatewayOutcome
    reason_code: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=128)
    semantic_target: SemanticTargetRef
    surface_outcome: SurfaceActionOutcome | None = None
