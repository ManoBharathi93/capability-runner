"""Anthropic messages translation behind the neutral ModelClient contract."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import SecretStr

from capability_runner.discovery.configuration import ModelProviderConfig
from capability_runner.discovery.model_client import ModelClientError, ModelRequest, ModelResponse

from ._http import json_object, normalize_http_error, normalize_transport_error, usage


class AnthropicModelClient:
    def __init__(
        self, config: ModelProviderConfig, *, client: httpx.AsyncClient | None = None
    ) -> None:
        if config.provider != "anthropic" or config.api_key is None:
            raise ValueError("AnthropicModelClient requires Anthropic credentials.")
        self._config = config
        self._api_key: SecretStr = config.api_key
        self._client = client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete(self, request: ModelRequest) -> ModelResponse:
        headers: dict[str, str] = {
            "x-api-key": self._api_key.get_secret_value(),
            "anthropic-version": "2023-06-01",
        }
        try:
            response = await self._client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=_payload(request, self._config.model),
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise normalize_http_error(error, "anthropic") from error
        except httpx.RequestError as error:
            raise normalize_transport_error(error, "anthropic") from error

        payload = json_object(response, "anthropic")
        try:
            content = payload["content"][0]["text"]
        except (IndexError, KeyError, TypeError) as error:
            raise ModelClientError(
                "INVALID_RESPONSE", "anthropic", "Response content is missing."
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ModelClientError("INVALID_RESPONSE", "anthropic", "Response content is invalid.")
        return ModelResponse(
            content=content, provider="anthropic", model=self._config.model, usage=usage(payload)
        )


def _payload(request: ModelRequest, model: str) -> dict[str, Any]:
    system = "\n".join(message.content for message in request.messages if message.role == "SYSTEM")
    messages = [
        {"role": message.role.lower(), "content": message.content}
        for message in request.messages
        if message.role != "SYSTEM"
    ]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens or 1_024,
    }
    if system:
        payload["system"] = system
    return payload
