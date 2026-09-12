"""Typed observations captured from a live surface.

The safe-evidence boundary matters here: models can carry operational notes or
other temporary values during execution, but a later recorder is responsible
for deciding what is persisted and what is redacted or dropped.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageObservation(ContractModel):
    kind: Literal["page"] = "page"
    url: HttpUrl | None = None
    title: str | None = Field(default=None, min_length=1)
    visible_text: str = Field(min_length=1)
    operational_values: tuple[SecretStr, ...] = Field(default_factory=tuple)


class DialogObservation(ContractModel):
    kind: Literal["dialog"] = "dialog"
    dialog_type: Literal["alert", "confirm", "prompt"]
    message: str = Field(min_length=1)
    blocking: bool = True


class OutcomeObservation(ContractModel):
    kind: Literal["outcome"] = "outcome"
    outcome: Literal["success", "business_outcome", "failure", "unknown"]
    summary: str = Field(min_length=1)
    details: str | None = Field(default=None, min_length=1)


type ObservationSpec = Annotated[
    PageObservation | DialogObservation | OutcomeObservation,
    Field(discriminator="kind"),
]
