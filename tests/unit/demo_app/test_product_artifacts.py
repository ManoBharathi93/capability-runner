from __future__ import annotations

import json
from pathlib import Path

import pytest

from capability_runner.application.demo_configuration import build_demo_capability
from capability_runner.contracts.evidence import EvidenceEvent
from demo_app.product_artifacts import ProductArtifactError, ProductArtifactIndex


def _write_run(root: Path, run_id: str, *, demo_kind: str = "replay") -> Path:
    run_directory = root / run_id
    run_directory.mkdir(parents=True)
    (run_directory / "summary.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "demo_kind": demo_kind,
                "status": "SUCCESS",
                "capability_id": "lookup_savings_balance",
                "capability_version": "1.0.0",
                "member_id": "must-not-leak",
            }
        ),
        encoding="utf-8",
    )
    event = EvidenceEvent(
        event_type="lifecycle",
        component="replay-engine",
        run_id=run_id,
        outcome="started",
        reason_code="REPLAY_STARTED",
    )
    (run_directory / "evidence.jsonl").write_text(
        event.model_dump_json() + "\n",
        encoding="utf-8",
    )
    return run_directory


def test_index_projects_only_validated_real_artifacts(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    curated = tmp_path / "curated"
    run_directory = _write_run(runtime, "replay-123")
    capability = build_demo_capability().definition
    capability_path = run_directory / "capabilities" / capability.capability_id / "1.0.0.json"
    capability_path.parent.mkdir(parents=True)
    capability_path.write_text(capability.model_dump_json(), encoding="utf-8")

    index = ProductArtifactIndex(runtime_root=runtime, curated_root=curated)

    assert index.overview()["run_count"] == 1
    assert index.list_capabilities()[0]["capability_id"] == capability.capability_id
    assert index.get_run("replay-123")["event_count"] == 1
    assert "member_id" not in index.get_run("replay-123")
    assert index.list_events("replay-123")[0]["reason_code"] == "REPLAY_STARTED"


def test_index_rejects_path_like_and_unknown_identifiers(tmp_path: Path) -> None:
    index = ProductArtifactIndex(
        runtime_root=tmp_path / "runtime",
        curated_root=tmp_path / "curated",
    )

    with pytest.raises(ProductArtifactError, match="invalid"):
        index.get_run("../summary")
    with pytest.raises(ProductArtifactError, match="not found"):
        index.get_capability("missing")


def test_index_exposes_only_persisted_interventions(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    run_directory = _write_run(runtime, "intervention-123", demo_kind="intervention")
    context = EvidenceEvent(
        event_type="intervention",
        component="run-coordinator",
        run_id="intervention-123",
        outcome="recorded",
        reason_code="INTERVENTION_CONTEXT_RECORDED",
        metadata={"intervention_id": "intervention-safe", "input_names": ["member_id"]},
    )
    with (run_directory / "evidence.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(context.model_dump_json() + "\n")

    index = ProductArtifactIndex(runtime_root=runtime, curated_root=tmp_path / "curated")

    intervention = index.get_intervention("intervention-safe")
    assert intervention["active"] is False
    assert intervention["control_state"] == "terminal"
    assert "input_names" not in intervention