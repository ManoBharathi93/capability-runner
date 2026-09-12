"""Typed target descriptions for trusted goals and invocations.

These models describe the target the live system may operate. They are not
execution logic and they do not resolve locators, open browsers, or touch
runtime state. Concrete target resolution and evidence handling happen in later
subsystems.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UrlTarget(ContractModel):
    kind: Literal["url"] = "url"
    url: HttpUrl
    label: str | None = Field(default=None, min_length=1)


class ProfileTarget(ContractModel):
    kind: Literal["profile"] = "profile"
    application: str = Field(min_length=1)
    profile: str = Field(min_length=1)
    entry_url: HttpUrl | None = None


type TargetSpec = Annotated[UrlTarget | ProfileTarget, Field(discriminator="kind")]
