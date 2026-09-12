from __future__ import annotations

import json
from pathlib import Path

import pytest

from demo_app.cli import main


@pytest.mark.live
def test_public_through_line_discovers_builds_stores_and_replays(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["demo", "through-line", "--output-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    run_directory = next(tmp_path.iterdir())
    summary = json.loads((run_directory / "summary.json").read_text(encoding="utf-8"))
    artifact_path = run_directory / summary["artifact_file"]
    serialized = (run_directory / "summary.json").read_text(
        encoding="utf-8"
    ) + (run_directory / "evidence.jsonl").read_text(encoding="utf-8")

    assert summary["discovery_result"] == "SUCCESS"
    assert summary["discovery_model_calls"] > 0
    assert summary["builder_model_calls"] == 0
    assert summary["replay_model_calls"] == 0
    assert summary["discovery_session_destroyed"] is True
    assert summary["fresh_replay_session"] is True
    assert summary["replay_result"] == "SUCCESS"
    assert summary["balance_minor_units"] == 438221
    assert summary["currency"] == "USD"
    assert artifact_path.is_file()
    assert not Path(summary["artifact_file"]).is_absolute()
    assert not Path(summary["evidence_file"]).is_absolute()
    assert "67890" not in serialized
    assert "12345" not in serialized
    assert "Discovery model calls:" in captured.out