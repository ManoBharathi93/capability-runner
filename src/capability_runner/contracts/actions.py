"""Typed action requests and results.

Action models can carry operational values such as typed fill inputs. Those
values are temporary execution inputs, not safe evidence on their own.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr

from .observations import ObservationSpec
from .targets import TargetSpec


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ClickAction(ContractModel):
    kind: Literal["click"] = "click"
    target: TargetSpec
    button: Literal["left", "middle", "right"] = "left"


class FillAction(ContractModel):
    kind: Literal["fill"] = "fill"
    target: TargetSpec
    value: SecretStr


class NavigateAction(ContractModel):
    kind: Literal["navigate"] = "navigate"
    url: HttpUrl


class WaitAction(ContractModel):
    kind: Literal["wait"] = "wait"
    seconds: float = Field(gt=0, le=600)


type ActionSpec = Annotated[
    ClickAction | FillAction | NavigateAction | WaitAction,
    Field(discriminator="kind"),
]


class ActionApplied(ContractModel):
    kind: Literal["applied"] = "applied"
    action: ActionSpec
    observation: ObservationSpec | None = None


class ActionRejected(ContractModel):
    kind: Literal["rejected"] = "rejected"
    reason: Literal["policy", "validation", "stale", "not_supported"]
    message: str = Field(min_length=1)
    action: ActionSpec | None = None


class ActionFailed(ContractModel):
    kind: Literal["failed"] = "failed"
    message: str = Field(min_length=1)
    action: ActionSpec | None = None


type ActionResult = Annotated[
    ActionApplied | ActionRejected | ActionFailed,
    Field(discriminator="kind"),
]
