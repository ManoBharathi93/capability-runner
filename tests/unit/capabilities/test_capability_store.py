from __future__ import annotations

import json
from pathlib import Path

import pytest

from capability_runner.capabilities.capability_store import (
    CapabilityLoadError,
    CapabilityStore,
    CapabilityVersionAlreadyExistsError,
)
from capability_runner.capabilities.capability_validator import CapabilityValidator
from capability_runner.contracts.capabilities import CapabilityDefinition


def _capability() -> CapabilityDefinition:
    payload = json.loads(
        Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json").read_text(
            encoding="utf-8"
        )
    )
    return CapabilityDefinition.model_validate(payload)


def test_store_saves_loads_lists_and_keeps_versions_immutable(tmp_path: Path) -> None:
    root = tmp_path / "capabilities"
    store = CapabilityStore(root)
    validated = CapabilityValidator().validate(_capability())

    path = store.save(validated)
    original_bytes = path.read_bytes()
    loaded = store.load("lookup_savings_balance", "1.0.0")

    assert path == root / "lookup_savings_balance" / "1.0.0.json"
    assert loaded == validated
    assert store.list_versions("lookup_savings_balance") == ("1.0.0",)
    with pytest.raises(CapabilityVersionAlreadyExistsError):
        store.save(validated)
    assert path.read_bytes() == original_bytes

    second_definition = validated.definition.model_copy(update={"capability_version": "1.0.1"})
    second_path = store.save(CapabilityValidator().validate(second_definition))
    assert second_path.name == "1.0.1.json"
    assert store.list_versions("lookup_savings_balance") == ("1.0.0", "1.0.1")


def test_store_rejects_invalid_paths_and_corrupt_or_invalid_files(tmp_path: Path) -> None:
    root = tmp_path / "capabilities"
    store = CapabilityStore(root)

    with pytest.raises(ValueError):
        store.load("../escape", "1.0.0")
    assert not root.exists()

    path = root / "lookup_savings_balance" / "1.0.0.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CapabilityLoadError):
        store.load("lookup_savings_balance", "1.0.0")

    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(CapabilityLoadError):
        store.load("lookup_savings_balance", "1.0.0")

    invalid_payload = _capability().model_dump(mode="json")
    invalid_payload["steps"][0]["action"]["value"]["name"] = "unknown"
    path.write_text(json.dumps(invalid_payload), encoding="utf-8")
    with pytest.raises(CapabilityLoadError):
        store.load("lookup_savings_balance", "1.0.0")
