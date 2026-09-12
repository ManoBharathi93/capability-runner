"""Typed session and control-ownership state.

The models in this module describe who controls a live session and at what
generation. They do not transfer control or dispatch browser actions; later
coordination code enforces the state machine and stale-action rejection.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AutomationOwner(ContractModel):
    kind: Literal["automation"] = "automation"
    run_id: str = Field(min_length=1)


class OperatorOwner(ContractModel):
    kind: Literal["operator"] = "operator"
    operator_id: str = Field(min_length=1)
    display_name: str | None = Field(default=None, min_length=1)


type SessionOwner = Annotated[
    AutomationOwner | OperatorOwner,
    Field(discriminator="kind"),
]


class SessionState(ContractModel):
    session_id: str = Field(min_length=1)
    control_state: Literal[
        "automation_controlled",
        "pause_requested",
        "operator_controlled",
        "resume_requested",
        "terminal",
    ]
    owner: SessionOwner
    control_generation: int = Field(ge=0)


SessionControlErrorCode = Literal[
    "SESSION_NOT_FOUND",
    "INVALID_STATE_TRANSITION",
    "NOT_AUTOMATION_OWNER",
    "NOT_OPERATOR_OWNER",
    "STALE_GENERATION",
    "DISPATCH_NOT_ALLOWED",
    "ACTION_IN_FLIGHT",
    "SESSION_STOPPED",
]


class SessionControllerError(RuntimeError):
    def __init__(self, code: SessionControlErrorCode, session_id: str | None, summary: str) -> None:
        if len(summary) > 160:
            raise ValueError("summary must not exceed 160 characters")
        super().__init__(summary)
        self.code = code
        self.session_id = session_id
        self.summary = summary
