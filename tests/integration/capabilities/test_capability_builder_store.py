from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from capability_runner.capabilities.capability_builder import CapabilityBuilder
from capability_runner.capabilities.capability_store import (
    CapabilityStore,
    CapabilityVersionAlreadyExistsError,
)
from capability_runner.contracts.capability_building import CapabilityBuildRequest
from capability_runner.contracts.discovery import DiscoveryResult


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request() -> CapabilityBuildRequest:
    result = DiscoveryResult.model_validate(
        {
            "outcome": "SUCCESS",
            "reason_code": "COMPLETED",
            "turns": 3,
            "actions": 2,
            "verified_targets": ["record.details.identity"],
            "completion_evidence": [
                {
                    "target": "record.details.identity",
                    "text_fingerprint": _fingerprint("private-record-42"),
                    "goal_span_action_target": "record.lookup.record_id",
                }
            ],
            "trace": [
                {
                    "turn": 1,
                    "decision_kind": "ACT",
                    "action_kind": "fill",
                    "semantic_target": "record.lookup.record_id",
                    "value_source": {"kind": "goal_span", "start": 7, "end": 24},
                    "gateway_outcome": "EXECUTED",
                    "observation_fingerprint": "0" * 64,
                    "outcome": "APPLIED",
                },
                {
                    "turn": 2,
                    "decision_kind": "ACT",
                    "action_kind": "click",
                    "semantic_target": "record.lookup.submit",
                    "gateway_outcome": "EXECUTED",
                    "observation_fingerprint": "1" * 64,
                    "outcome": "APPLIED",
                },
                {
                    "turn": 3,
                    "decision_kind": "COMPLETE",
                    "observation_fingerprint": "2" * 64,
                    "outcome": "VERIFIED",
                },
            ],
        }
    )
    return CapabilityBuildRequest.model_validate(
        {
            "capability_id": "lookup_record",
            "capability_version": "1.0.0",
            "name": "Lookup record",
            "description": "Find a record by its private identifier.",
            "discovery_result": result,
            "application_requirement": {
                "application_family": "records",
                "surface_kind": "browser",
            },
            "input_sensitivity": [
                {
                    "action_target": {"value": "record.lookup.record_id"},
                    "sensitive": True,
                }
            ],
            "success_templates": [
                {
                    "kind": "input_equals",
                    "target": {"value": "record.details.identity"},
                    "input_action_target": {"value": "record.lookup.record_id"},
                }
            ],
        }
    )


def test_builder_validator_and_immutable_store_round_trip(tmp_path: Path) -> None:
    built = CapabilityBuilder().build(_request())
    store = CapabilityStore(tmp_path / "capabilities")

    artifact_path = store.save(built)
    loaded = store.load("lookup_record", "1.0.0")
    persisted = artifact_path.read_text(encoding="utf-8")

    assert loaded == built
    assert json.loads(persisted) == built.definition.model_dump(mode="json")
    assert "private-record-42" not in persisted
    with pytest.raises(CapabilityVersionAlreadyExistsError):
        store.save(built)