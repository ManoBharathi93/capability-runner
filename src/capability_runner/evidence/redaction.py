from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any, cast
from uuid import UUID

from pydantic import SecretStr

REDACTION_PLACEHOLDER = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {"password", "passwd", "secret", "token", "api_key", "authorization", "cookie", "set_cookie"}
)


@dataclass(frozen=True, slots=True)
class RedactionContext:
    explicit_values: frozenset[str] = frozenset()
    placeholder: str = REDACTION_PLACEHOLDER

    def with_explicit_values(self, *values: str) -> RedactionContext:
        filtered_values = frozenset(value for value in (*self.explicit_values, *values) if value)
        return RedactionContext(explicit_values=filtered_values, placeholder=self.placeholder)


def _redact_text(value: str, context: RedactionContext) -> str:
    redacted = value
    for sensitive_value in sorted(context.explicit_values, key=len, reverse=True):
        if sensitive_value:
            redacted = redacted.replace(sensitive_value, context.placeholder)
    return redacted


def redact_value(value: object, context: RedactionContext, key: str | None = None) -> object:
    if isinstance(value, SecretStr):
        return context.placeholder
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if key is not None and key.casefold() in SENSITIVE_KEYS:
            return context.placeholder
        return _redact_text(value, context)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return value.isoformat()
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, list):
        items = cast(list[Any], value)
        return [redact_value(item, context) for item in items]
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        mapping = cast(Mapping[object, Any], value)
        for raw_key, item in mapping.items():
            if not isinstance(raw_key, str):
                raise TypeError("metadata keys must be strings")
            if raw_key.casefold() in SENSITIVE_KEYS:
                sanitized[raw_key] = context.placeholder
            else:
                sanitized[raw_key] = redact_value(item, context, raw_key)
        return sanitized
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")


def redact_event_payload(
    payload: dict[str, object], context: RedactionContext
) -> dict[str, object]:
    sanitized = redact_value(payload, context)
    if not isinstance(sanitized, dict):
        raise TypeError("event payload must be a mapping")
    return cast(dict[str, object], sanitized)
