"""Shared HTTP normalization helpers used only by provider adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import httpx

from capability_runner.discovery.model_client import ModelClientError, ModelErrorCode


def normalize_http_error(error: httpx.HTTPStatusError, provider: str) -> ModelClientError:
    status = error.response.status_code
    code: ModelErrorCode
    if status in {401, 403}:
        code = "AUTHENTICATION_ERROR"
    elif status == 429:
        code = "RATE_LIMITED"
    else:
        code = "PROVIDER_ERROR"
    return ModelClientError(code, provider, f"Provider returned HTTP {status}.")


def normalize_transport_error(error: httpx.RequestError, provider: str) -> ModelClientError:
    if isinstance(error, httpx.TimeoutException):
        code: ModelErrorCode = "TIMEOUT"
        message = "Provider request timed out."
    elif isinstance(error, httpx.ConnectError):
        code = "CONNECTION_ERROR"
        message = "Provider connection failed."
    else:
        code = "PROVIDER_ERROR"
        message = "Provider request failed."
    return ModelClientError(code, provider, message)


def json_object(response: httpx.Response, provider: str) -> Mapping[str, Any]:
    try:
        payload = cast(object, response.json())
    except ValueError as error:
        raise ModelClientError(
            "INVALID_RESPONSE", provider, "Provider returned invalid JSON."
        ) from error
    if not isinstance(payload, dict):
        raise ModelClientError(
            "INVALID_RESPONSE", provider, "Provider response must be a JSON object."
        )
    return cast(Mapping[str, Any], payload)


def usage(payload: Mapping[str, Any]) -> dict[str, int] | None:
    raw_usage = cast(object, payload.get("usage"))
    if not isinstance(raw_usage, dict):
        return None
    normalized = {
        key: value
        for key, value in cast(Mapping[object, object], raw_usage).items()
        if isinstance(key, str) and isinstance(value, int)
    }
    return normalized or None
