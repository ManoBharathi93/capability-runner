"""OpenAI chat-completions translation behind the neutral ModelClient contract."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import SecretStr

from capability_runner.discovery.configuration import ModelProviderConfig
from capability_runner.discovery.model_client import ModelClientError, ModelRequest, ModelResponse

from ._http import json_object, normalize_http_error, normalize_transport_error, usage


class OpenAIModelClient:
    def __init__(
        self, config: ModelProviderConfig, *, client: httpx.AsyncClient | None = None
    ) -> None:
        if config.provider != "openai" or config.api_key is None:
            raise ValueError("OpenAIModelClient requires OpenAI credentials.")
        self._config = config
        self._api_key: SecretStr = config.api_key
        self._client = client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            response = await self._client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
                json=_payload(request, self._config.model),
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise normalize_http_error(error, "openai") from error
        except httpx.RequestError as error:
            raise normalize_transport_error(error, "openai") from error

        payload = json_object(response, "openai")
        try:
            content = payload["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as error:
            raise ModelClientError(
                "INVALID_RESPONSE", "openai", "Response content is missing."
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ModelClientError("INVALID_RESPONSE", "openai", "Response content is invalid.")
        return ModelResponse(
            content=content, provider="openai", model=self._config.model, usage=usage(payload)
        )


def _payload(request: ModelRequest, model: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": message.role.lower(), "content": message.content}
            for message in request.messages
        ],
        "temperature": request.temperature,
    }
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    return payload
