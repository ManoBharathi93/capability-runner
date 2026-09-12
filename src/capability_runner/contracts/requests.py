"""Typed requests for discovery and replay.

These request models carry temporary operational values such as typed input
parameters. They are intentionally separate from safe evidence; later evidence
recording decides what can be persisted or redacted.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from .surfaces import SemanticTargetRef
from .targets import TargetSpec


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicParameter(ContractModel):
    kind: Literal["public"] = "public"
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)


class SensitiveParameter(ContractModel):
    kind: Literal["sensitive"] = "sensitive"
    name: str = Field(min_length=1)
    value: SecretStr


type RequestParameter = Annotated[
    PublicParameter | SensitiveParameter,
    Field(discriminator="kind"),
]


def _empty_request_parameters() -> list[RequestParameter]:
    return []


class DiscoveryRequest(ContractModel):
    goal: str = Field(min_length=1, max_length=4000)
    target: TargetSpec
    max_steps: int = Field(default=20, ge=1)
    timeout_seconds: float = Field(default=300.0, gt=0)
    parameters: list[RequestParameter] = Field(default_factory=_empty_request_parameters)
    required_completion_targets: tuple[SemanticTargetRef, ...] = Field(
        default_factory=tuple,
        max_length=24,
    )

    @field_validator("goal")
    @classmethod
    def nonempty_goal(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A nonempty workflow goal is required")
        return value


class ReplayRequest(ContractModel):
    capability_id: str = Field(min_length=1)
    target: TargetSpec
    parameters: list[RequestParameter] = Field(default_factory=_empty_request_parameters)
    strict: bool = True
