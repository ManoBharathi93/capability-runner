from __future__ import annotations

import json
from pathlib import Path

import pytest

from demo_app.cli import LIVE_CONFIGURATION_MESSAGE, main


def test_demo_help_lists_exact_reviewer_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["demo", "--help"])

    assert exit_info.value.code == 0
    output = capsys.readouterr().out
    assert "through-line" in output
    assert "intervention" in output
    assert "exception" in output


def test_through_line_missing_configuration_fails_safely(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["demo", "through-line", "--output-root", str(tmp_path)],
        environment={},
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.strip() == LIVE_CONFIGURATION_MESSAGE
    assert list(tmp_path.iterdir()) == []


def test_exception_command_writes_safe_relative_runtime_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["demo", "exception", "--output-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    run_directories = list(tmp_path.iterdir())
    assert len(run_directories) == 1
    summary_path = run_directories[0] / "summary.json"
    evidence_path = run_directories[0] / "evidence.jsonl"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    serialized = summary_path.read_text(encoding="utf-8") + evidence_path.read_text(
        encoding="utf-8"
    )

    assert summary["replay_result"] == "BUSINESS_OUTCOME"
    assert summary["business_outcome"] == "MEMBER_NOT_FOUND"
    assert summary["replay_model_calls"] == 0
    assert not Path(summary["evidence_file"]).is_absolute()
    assert summary["artifact_file"] is None
    assert "00000" not in serialized
    assert "REPLAY_STARTED" in serialized
    assert "REPLAY_COMPLETED" in serialized
    assert "BUSINESS_OUTCOME" in captured.out


def test_intervention_command_uses_http_handoff_without_repeating_actions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["demo", "intervention", "--output-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    run_directory = next(tmp_path.iterdir())
    summary = json.loads((run_directory / "summary.json").read_text(encoding="utf-8"))
    serialized = (run_directory / "summary.json").read_text(
        encoding="utf-8"
    ) + (run_directory / "evidence.jsonl").read_text(encoding="utf-8")

    assert summary["operator_mode"] == "automated_http"
    assert summary["same_surface_session"] is True
    assert summary["generation_before"] == 0
    assert summary["generation_after"] == 3
    assert summary["replay_result"] == "SUCCESS"
    assert summary["balance_minor_units"] == 98765
    assert summary["currency"] == "USD"
    assert summary["repeated_automation_side_effects"] is False
    assert "67890" not in serialized
    assert "INTERVENTION_CONTEXT_RECORDED" in serialized
    assert '"current_state":"blocked_before_dispatch"' in serialized
    assert '"action_effect_state":"NOT_EXECUTED"' in serialized
    assert "REPLAY_RESUME_STARTED" in serialized
    assert "Fresh state validation: PASS" in captured.out