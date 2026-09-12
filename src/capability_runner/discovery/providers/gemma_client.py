"""Hosted Gemma OpenAI-compatible chat-completions adapter."""

from __future__ import annotations

from typing import Any

import httpx

from capability_runner.discovery.configuration import ModelProviderConfig
from capability_runner.discovery.model_client import ModelClientError, ModelRequest, ModelResponse

from ._http import json_object, normalize_http_error, normalize_transport_error, usage


class GemmaModelClient:
    def __init__(
        self, config: ModelProviderConfig, *, client: httpx.AsyncClient | None = None
    ) -> None:
        if config.provider != "gemma" or config.base_url is None:
            raise ValueError("GemmaModelClient requires a Gemma base URL.")
        self._config = config
        self._base_url: str = config.base_url
        self._client = client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete(self, request: ModelRequest) -> ModelResponse:
        headers: dict[str, str] = {}
        if self._config.api_key is not None:
            headers["Authorization"] = f"Bearer {self._config.api_key.get_secret_value()}"
        try:
            response = await self._client.post(
                f"{self._base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=_payload(request, self._config.model),
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise normalize_http_error(error, "gemma") from error
        except httpx.RequestError as error:
            raise normalize_transport_error(error, "gemma") from error

        payload = json_object(response, "gemma")
        try:
            content = payload["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as error:
            raise ModelClientError(
                "INVALID_RESPONSE", "gemma", "Response content is missing."
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ModelClientError("INVALID_RESPONSE", "gemma", "Response content is invalid.")
        return ModelResponse(
            content=content, provider="gemma", model=self._config.model, usage=usage(payload)
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
