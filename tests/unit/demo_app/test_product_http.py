from __future__ import annotations

from pathlib import Path
from typing import Any

from capability_runner.application.demo_configuration import (
    DEMO_CAPABILITY_ID,
    DEMO_CAPABILITY_VERSION,
)
from capability_runner.contracts.operator_console import OperatorActionSubmission
from capability_runner.discovery.model_client import ModelClient
from demo_app.discovery_workspace import DiscoveryWorkspace
from demo_app.product_artifacts import ProductArtifactIndex
from demo_app.product_http import create_product_app
from demo_app.reviewer_runtime import DemoRunResult


class RecordingWorkflows:
    def __init__(self, run_directory: Path) -> None:
        self.run_directory = run_directory
        self.replay_member_ids: list[str] = []
        self.actions: list[OperatorActionSubmission] = []
        self.goals: list[str] = []

    def discover(self) -> DemoRunResult:
        return self._result()

    def replay(self, member_id: str) -> DemoRunResult:
        self.replay_member_ids.append(member_id)
        return self._result()

    def list_active_interventions(self) -> list[dict[str, object]]:
        return []

    def start_intervention(self) -> dict[str, object]:
        return {"intervention_id": "intervention-live", "active": True}

    def get_intervention(self, intervention_id: str) -> dict[str, object]:
        return {"intervention_id": intervention_id, "active": True}

    def get_controls(self, intervention_id: str) -> dict[str, object]:
        return {"controls": [{"label": "Savings", "action_kind": "click"}]}

    def get_view(self, intervention_id: str) -> tuple[bytes, str]:
        return b"\x89PNG\r\n\x1a\nview", "image/png"

    def execute_action(
        self,
        intervention_id: str,
        submission: OperatorActionSubmission,
    ) -> dict[str, object]:
        self.actions.append(submission)
        return {"executed": True}

    def return_control(self, intervention_id: str) -> dict[str, object]:
        return {"run_id": "run-1", "status": "SUCCESS"}

    def stop(self, intervention_id: str) -> dict[str, object]:
        return {"control_state": "terminal"}

    def _result(self) -> DemoRunResult:
        return DemoRunResult(
            run_directory=self.run_directory,
            summary_path=self.run_directory / "summary.json",
            summary={"run_id": "run-1"},
        )


def _app(tmp_path: Path) -> tuple[Any, RecordingWorkflows]:
    runtime = tmp_path / "runtime"
    run_directory = runtime / "run-1"
    run_directory.mkdir(parents=True)
    (run_directory / "summary.json").write_text(
        '{"schema_version":1,"run_id":"run-1","demo_kind":"replay","status":"SUCCESS"}',
        encoding="utf-8",
    )
    (run_directory / "evidence.jsonl").write_text("", encoding="utf-8")
    workflows = RecordingWorkflows(run_directory)

    class RecordingWorkspace(DiscoveryWorkspace):
        def start(
            self,
            goal: str,
            application: str,
            url: str | None = None,
            *,
            model: ModelClient | None = None,
        ) -> dict[str, object]:
            workflows.goals.append(goal)
            return {"run_id": "run-1", "status": "RUNNING"}

    app = create_product_app(
        artifact_index=ProductArtifactIndex(
            runtime_root=runtime,
            curated_root=tmp_path / "curated",
        ),
        workflows=workflows,
        workspace=RecordingWorkspace(runtime, lambda: {}),
        web_root=tmp_path / "missing-web",
    )
    app.config["TESTING"] = True
    return app, workflows


def test_read_routes_return_only_indexed_artifacts(tmp_path: Path) -> None:
    app, _ = _app(tmp_path)
    with app.test_client() as client:
        overview = client.get("/api/overview")
        runs = client.get("/api/runs")
        unknown = client.get("/api/runs/../secret")

    assert overview.status_code == 200
    assert overview.get_json()["run_count"] == 1
    assert runs.get_json()["runs"][0]["run_id"] == "run-1"
    assert unknown.status_code == 404


def test_discovery_accepts_arbitrary_goal_and_forwards_it(tmp_path: Path) -> None:
    app, workflows = _app(tmp_path)
    with app.test_client() as client:
        for goal in ["Do something else", "Look up member 67890.", "Delete every member."]:
            accepted = client.post("/api/discovery", json={"goal": goal})
            assert accepted.status_code == 202
        for goal in ["", "   ", "x" * 4001]:
            assert client.post("/api/discovery", json={"goal": goal}).status_code == 422
    assert workflows.goals == ["Do something else", "Look up member 67890.", "Delete every member."]


def test_replay_delegates_sensitive_input_without_echoing_it(tmp_path: Path) -> None:
    app, workflows = _app(tmp_path)
    with app.test_client() as client:
        response = client.post(
            "/api/replay",
            json={
                "capability_id": DEMO_CAPABILITY_ID,
                "version": DEMO_CAPABILITY_VERSION,
                "member_id": "private-member-id",
            },
        )

    assert response.status_code == 201
    assert workflows.replay_member_ids == ["private-member-id"]
    assert "private-member-id" not in response.get_data(as_text=True)


def test_operator_routes_delegate_and_keep_values_out_of_responses(tmp_path: Path) -> None:
    app, workflows = _app(tmp_path)
    with app.test_client() as client:
        started = client.post("/api/interventions")
        view = client.get("/api/interventions/intervention-live/view")
        action = client.post(
            "/api/interventions/intervention-live/actions",
            json={
                "semantic_target": "member.search.member_id",
                "action_kind": "fill",
                "value": "private-member-id",
            },
        )
        returned = client.post("/api/interventions/intervention-live/return-control")

    assert started.status_code == 201
    assert view.headers["Cache-Control"] == "no-store, max-age=0"
    assert action.status_code == 200
    assert workflows.actions[0].value is not None
    assert workflows.actions[0].value.get_secret_value() == "private-member-id"
    assert "private-member-id" not in action.get_data(as_text=True)
    assert returned.get_json()["status"] == "SUCCESS"
