from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


EvidenceEventType = Literal["lifecycle", "action", "policy", "outcome", "error", "intervention"]


def _validate_metadata_value(value: Any) -> Any:
    if isinstance(value, SecretStr):
        return value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        items = cast(list[Any], value)
        return [_validate_metadata_value(item) for item in items]
    if isinstance(value, dict):
        validated: dict[str, object] = {}
        mapping = cast(Mapping[object, Any], value)
        for raw_key, item in mapping.items():
            if not isinstance(raw_key, str):
                raise ValueError("metadata keys must be strings")
            validated[raw_key] = _validate_metadata_value(item)
        return validated
    raise ValueError(f"unsupported metadata value: {type(value).__name__}")


class EvidenceEvent(ContractModel):
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: EvidenceEventType
    component: str = Field(min_length=1, max_length=80)
    run_id: str = Field(min_length=1, max_length=128)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    step_id: str | None = Field(default=None, min_length=1, max_length=128)
    action_id: str | None = Field(default=None, min_length=1, max_length=128)
    outcome: str | None = Field(default=None, min_length=1, max_length=80)
    reason_code: str | None = Field(default=None, min_length=1, max_length=80)
    summary: str | None = Field(default=None, min_length=1, max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def _normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware UTC")
        return value.astimezone(UTC)

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("metadata must be a mapping")
        validated = _validate_metadata_value(value)
        if not isinstance(validated, dict):
            raise ValueError("metadata must be a mapping")
        return cast(dict[str, Any], validated)
