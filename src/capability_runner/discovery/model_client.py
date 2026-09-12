"""Provider-neutral contracts for future discovery model invocation."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

ModelMessageRole = Literal["SYSTEM", "USER", "ASSISTANT"]
ModelErrorCode = Literal[
    "AUTHENTICATION_ERROR",
    "RATE_LIMITED",
    "TIMEOUT",
    "CONNECTION_ERROR",
    "INVALID_RESPONSE",
    "PROVIDER_ERROR",
]


class ModelMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: ModelMessageRole
    content: str = Field(min_length=1, max_length=20_000)


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    messages: tuple[ModelMessage, ...] = Field(min_length=1, max_length=32)
    temperature: float = Field(default=0, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=4_096)
    response_schema: dict[str, object] | None = None


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(min_length=1, max_length=100_000)
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=256)
    usage: dict[str, int] | None = None


class ModelClientError(RuntimeError):
    def __init__(self, code: ModelErrorCode, provider: str, diagnostic: str) -> None:
        super().__init__(f"{provider}: {diagnostic}")
        self.code = code
        self.provider = provider
        self.diagnostic = diagnostic


class ModelClient(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Return a normalized response or raise a normalized model error."""
        ...
