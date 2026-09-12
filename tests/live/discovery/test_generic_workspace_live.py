"""Explicit real-provider acceptance; excluded from the ordinary pytest command."""

import json
from pathlib import Path

import pytest

from demo_app.evaluation import evaluate, load_suite


@pytest.mark.live
@pytest.mark.parametrize("case_index", [0, 1])
def test_live_generic_workspace_acceptance(tmp_path: Path, case_index: int) -> None:
    suite = load_suite(Path("evals/banking-live.yaml"), live=True)
    selected = suite.model_copy(update={"cases": (suite.cases[case_index],)})
    path = tmp_path / "live.json"
    path.write_text(selected.model_dump_json(), encoding="utf-8")
    report_path, _ = evaluate(path, live=True, phase="discovery")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["metrics"]["passed"] == 1
    assert report["metrics"]["replay_model_calls"] == 0
