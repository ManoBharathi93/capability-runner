"""Local product HTTP composition for the optional P5.4b frontend."""

from __future__ import annotations

import atexit
import os
import threading
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast
from uuid import uuid4

from flask import Flask, Response, jsonify, request, send_from_directory
from pydantic import ValidationError

from capability_runner.application.demo_configuration import (
    DEMO_CAPABILITY_ID,
    DEMO_CAPABILITY_VERSION,
)
from capability_runner.application.operator_console import OperatorConsoleError
from capability_runner.contracts.operator_console import OperatorActionSubmission
from capability_runner.discovery.configuration import ModelConfigurationError
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interfaces.async_core_runner import AsyncCoreRunner

from .app import DemoScenario
from .app import create_app as create_target_app
from .discovery_workspace import DiscoveryWorkspace
from .product_artifacts import ProductArtifactError, ProductArtifactIndex
from .reviewer_runtime import (
    DEFAULT_OUTPUT_ROOT,
    DISCOVERY_MEMBER_ID,
    DemoRunError,
    DemoRunResult,
    close_intervention,
    prepare_intervention,
    run_replay,
    run_through_line,
    serve_app,
    verify_intervention,
    write_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURATED_ROOT = PROJECT_ROOT / "evidence"
DEFAULT_WEB_ROOT = PROJECT_ROOT / "web" / "dist"


class ProductWorkflow(Protocol):
    def discover(self) -> DemoRunResult: ...

    def replay(self, member_id: str) -> DemoRunResult: ...

    def list_active_interventions(self) -> list[dict[str, object]]: ...

    def start_intervention(self) -> dict[str, object]: ...

    def get_intervention(self, intervention_id: str) -> dict[str, object]: ...

    def get_controls(self, intervention_id: str) -> dict[str, object]: ...

    def get_view(self, intervention_id: str) -> tuple[bytes, str]: ...

    def execute_action(
        self,
        intervention_id: str,
        submission: OperatorActionSubmission,
    ) -> dict[str, object]: ...

    def return_control(self, intervention_id: str) -> dict[str, object]: ...

    def stop(self, intervention_id: str) -> dict[str, object]: ...


@dataclass(slots=True)
class _LiveProductIntervention:
    target_context: AbstractContextManager[str]
    runner: AsyncCoreRunner
    execution: Any
    recorder: EvidenceRecorder


class ProductWorkflowService:
    def __init__(
        self,
        *,
        output_root: Path,
        environment_provider: Callable[[], Mapping[str, str]],
    ) -> None:
        self._output_root = output_root
        self._environment_provider = environment_provider
        self._live: dict[str, _LiveProductIntervention] = {}
        self._lock = threading.Lock()

    def discover(self) -> DemoRunResult:
        return run_through_line(
            environment=self._environment_provider(),
            output_root=self._output_root,
        )

    def replay(self, member_id: str) -> DemoRunResult:
        return run_replay(member_id=member_id, output_root=self._output_root)

    def list_active_interventions(self) -> list[dict[str, object]]:
        with self._lock:
            identifiers = tuple(self._live)
        active: list[dict[str, object]] = []
        for intervention_id in identifiers:
            try:
                active.append(self.get_intervention(intervention_id))
            except OperatorConsoleError:
                continue
        return active

    def start_intervention(self) -> dict[str, object]:
        with self._lock:
            if self._live:
                intervention_id = next(iter(self._live))
                return self._status_dto(intervention_id, self._live[intervention_id])

            run_id = f"intervention-{uuid4().hex}"
            recorder = EvidenceRecorder(
                self._output_root,
                run_id,
                redaction_context=RedactionContext(
                    explicit_values=frozenset({DISCOVERY_MEMBER_ID})
                ),
            )
            target_context = serve_app(create_target_app(scenario=DemoScenario(mode="normal")))
            base_url = target_context.__enter__()
            runner = AsyncCoreRunner(timeout_seconds=60)
            try:
                execution = runner.run(
                    prepare_intervention(
                        base_url=base_url,
                        run_id=run_id,
                        recorder=recorder,
                    )
                )
            except Exception:
                runner.close()
                target_context.__exit__(None, None, None)
                raise
            intervention_id = execution.record.intervention_id
            live = _LiveProductIntervention(
                target_context=target_context,
                runner=runner,
                execution=execution,
                recorder=recorder,
            )
            self._live[intervention_id] = live
            return self._status_dto(intervention_id, live)

    def get_intervention(self, intervention_id: str) -> dict[str, object]:
        return self._status_dto(intervention_id, self._get_live(intervention_id))

    def get_controls(self, intervention_id: str) -> dict[str, object]:
        live = self._get_live(intervention_id)
        controls = live.runner.run(live.execution.console.get_available_controls(intervention_id))
        return {"controls": [control.model_dump(mode="json") for control in controls]}

    def get_view(self, intervention_id: str) -> tuple[bytes, str]:
        live = self._get_live(intervention_id)
        view = live.runner.run(live.execution.console.capture_view(intervention_id))
        return view.content, view.mime_type

    def execute_action(
        self,
        intervention_id: str,
        submission: OperatorActionSubmission,
    ) -> dict[str, object]:
        live = self._get_live(intervention_id)
        result = live.runner.run(live.execution.console.execute_action(intervention_id, submission))
        return result.model_dump(mode="json")

    def return_control(self, intervention_id: str) -> dict[str, object]:
        live = self._get_live(intervention_id)
        live.runner.run(live.execution.console.return_control(intervention_id))
        try:
            resumed = live.runner.run(live.execution.coordinator.resume(intervention_id))
        finally:
            self._close_live(intervention_id, live)
        verify_intervention(live.execution, resumed)
        replay_result = resumed.replay_result
        if replay_result is None:
            raise DemoRunError("Replay continuation returned no result.")
        summary: dict[str, object] = {
            "schema_version": 1,
            "run_id": live.execution.record.run_id,
            "demo_kind": "intervention",
            "status": "SUCCESS",
            "capability_id": DEMO_CAPABILITY_ID,
            "capability_version": DEMO_CAPABILITY_VERSION,
            "operator_mode": "product_http",
            "blocked_action": "member.accounts.savings",
            "same_surface_session": live.execution.record.surface_session == live.execution.session,
            "generation_before": resumed.generation_before,
            "generation_after": resumed.generation_after,
            "replay_result": replay_result.outcome,
            "outputs": replay_result.outputs,
            "repeated_automation_side_effects": (
                sum(live.execution.automation_counter.executed.values()) != 3
            ),
            "discovery_model_calls": 0,
            "builder_model_calls": 0,
            "replay_model_calls": 0,
            "browser_action_count": (
                sum(live.execution.automation_counter.executed.values())
                + sum(live.execution.operator_counter.executed.values())
            ),
        }
        return write_summary(live.recorder.run_directory, summary).summary

    def stop(self, intervention_id: str) -> dict[str, object]:
        live = self._get_live(intervention_id)
        result = live.runner.run(live.execution.console.stop(intervention_id))
        self._close_live(intervention_id, live)
        write_summary(
            live.recorder.run_directory,
            {
                "schema_version": 1,
                "run_id": live.execution.record.run_id,
                "demo_kind": "intervention",
                "status": "STOPPED",
                "capability_id": DEMO_CAPABILITY_ID,
                "capability_version": DEMO_CAPABILITY_VERSION,
                "blocked_action": "member.accounts.savings",
                "replay_result": None,
            },
        )
        return result.model_dump(mode="json")

    def close(self) -> None:
        with self._lock:
            active = tuple(self._live.items())
        for intervention_id, live in active:
            try:
                live.runner.run(live.execution.console.stop(intervention_id))
            except Exception:
                pass
            self._close_live(intervention_id, live)

    def _status_dto(
        self,
        intervention_id: str,
        live: _LiveProductIntervention,
    ) -> dict[str, object]:
        status = live.runner.run(live.execution.console.get_status(intervention_id))
        return {
            **status.model_dump(mode="json"),
            "run_id": live.execution.record.run_id,
            "capability_id": DEMO_CAPABILITY_ID,
            "active": True,
            "blocked_action": "member.accounts.savings",
        }

    def _get_live(self, intervention_id: str) -> _LiveProductIntervention:
        with self._lock:
            live = self._live.get(intervention_id)
        if live is None:
            raise OperatorConsoleError(
                "INTERVENTION_NOT_ACTIVE",
                "Intervention is not active in this server process.",
                409,
            )
        return live

    def _close_live(
        self,
        intervention_id: str,
        live: _LiveProductIntervention,
    ) -> None:
        try:
            live.runner.run(close_intervention(live.execution))
        finally:
            live.runner.close()
            live.target_context.__exit__(None, None, None)
            with self._lock:
                self._live.pop(intervention_id, None)


def create_product_app(
    *,
    artifact_index: ProductArtifactIndex | None = None,
    workflows: ProductWorkflow | None = None,
    web_root: Path = DEFAULT_WEB_ROOT,
    workspace: DiscoveryWorkspace | None = None,
) -> Flask:
    index = artifact_index or ProductArtifactIndex(
        runtime_root=PROJECT_ROOT / DEFAULT_OUTPUT_ROOT,
        curated_root=DEFAULT_CURATED_ROOT,
    )
    workflow_service = workflows or ProductWorkflowService(
        output_root=PROJECT_ROOT / DEFAULT_OUTPUT_ROOT,
        environment_provider=_load_environment,
    )
    discovery_workspace = workspace or DiscoveryWorkspace(
        PROJECT_ROOT / DEFAULT_OUTPUT_ROOT, _load_environment
    )
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 32_000

    @app.get("/api/overview")
    def overview():
        payload = index.overview()
        payload["active_run_count"] = len(workflow_service.list_active_interventions())
        return jsonify(payload)

    @app.get("/api/capabilities")
    def capabilities():
        return jsonify({"capabilities": index.list_capabilities()})

    @app.get("/api/capabilities/<capability_id>")
    def capability(capability_id: str):
        try:
            return jsonify(index.get_capability(capability_id, request.args.get("version")))
        except ProductArtifactError as error:
            return _safe_error("CAPABILITY_NOT_FOUND", str(error), 404)

    @app.get("/api/runs")
    def runs():
        return jsonify({"runs": index.list_runs()})

    @app.get("/api/runs/<run_id>")
    def run_detail(run_id: str):
        try:
            return jsonify(index.get_run(run_id))
        except ProductArtifactError as error:
            return _safe_error("RUN_NOT_FOUND", str(error), 404)

    @app.get("/api/runs/<run_id>/events")
    def run_events(run_id: str):
        try:
            return jsonify({"events": index.list_events(run_id)})
        except ProductArtifactError as error:
            return _safe_error("RUN_NOT_FOUND", str(error), 404)

    @app.post("/api/discovery")
    def discovery():
        payload = request.get_json(silent=True)
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("goal"), str)
            or not payload["goal"].strip()
            or len(payload["goal"]) > 4000
        ):
            return _safe_error(
                "INVALID_GOAL", "Enter a workflow goal of 1 to 4,000 characters.", 422
            )
        application = payload.get("application", "corebank-known")
        url = payload.get("url")
        if application not in {"corebank-known", "corebank", "bank-b", "new"} or (
            url is not None and not isinstance(url, str)
        ):
            return _safe_error("INVALID_APPLICATION", "Select a configured application.", 422)
        try:
            return jsonify(discovery_workspace.start(payload["goal"], application, url)), 202
        except ModelConfigurationError:
            return _safe_error(
                "MODEL_CONFIGURATION_UNAVAILABLE", "Live model configuration is unavailable.", 503
            )
        except ValueError:
            return _safe_error(
                "DISCOVERY_NOT_STARTED",
                "Check application allowlist and active session limits.",
                422,
            )

    @app.get("/api/discovery/<run_id>")
    def discovery_status(run_id: str):
        try:
            return jsonify(discovery_workspace.status(run_id))
        except KeyError:
            return _safe_error("RUN_NOT_ACTIVE", "Run is not in this server process.", 404)

    @app.get("/api/discovery/<run_id>/view")
    def discovery_view(run_id: str):
        try:
            content = discovery_workspace.view(run_id)
        except (KeyError, ValueError):
            return _safe_error("VIEW_NOT_READY", "Managed browser view is not available yet.", 409)
        return Response(
            content,
            mimetype="image/png",
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.post("/api/discovery/<run_id>/replay")
    def discovery_replay(run_id: str):
        payload = request.get_json(silent=True)
        inputs = payload.get("inputs") if isinstance(payload, dict) else None
        if (
            not isinstance(inputs, dict)
            or len(inputs) > 8
            or any(
                not isinstance(key, str)
                or not isinstance(value, str)
                or not value
                or len(value) > 128
                for key, value in inputs.items()
            )
        ):
            return _safe_error("INVALID_INPUTS", "Supply the capability's typed inputs.", 422)
        try:
            return jsonify(discovery_workspace.replay(run_id, inputs))
        except (KeyError, ValueError):
            return _safe_error("REPLAY_UNAVAILABLE", "A stored capability is required.", 409)
        except Exception:
            return _safe_error("REPLAY_FAILED", "Replay could not be completed.", 409)

    @app.post("/api/replay")
    def replay():
        raw_payload: object = request.get_json(silent=True)
        if not isinstance(raw_payload, dict):
            return _safe_error("INVALID_REQUEST", "A JSON object is required.", 400)
        payload = cast(dict[str, object], raw_payload)
        capability_id = payload.get("capability_id")
        if isinstance(capability_id, str) and capability_id.startswith("workflow_"):
            inputs = payload.get("inputs")
            if (
                not isinstance(inputs, dict)
                or len(inputs) > 8
                or any(
                    not isinstance(key, str) or not isinstance(value, str) or len(value) > 128
                    for key, value in inputs.items()
                )
            ):
                return _safe_error("INVALID_INPUTS", "Supply the declared capability inputs.", 422)
            try:
                summary = discovery_workspace.replay_stored(
                    capability_id, str(payload.get("version", "")), inputs
                )
                return jsonify({"run": summary}), 201
            except (ValueError, OSError):
                return _safe_error(
                    "REPLAY_UNAVAILABLE", "Stored package or application scope unavailable.", 409
                )
        member_id = payload.get("member_id")
        if (
            payload.get("capability_id") != DEMO_CAPABILITY_ID
            or payload.get("version") != DEMO_CAPABILITY_VERSION
            or not isinstance(member_id, str)
            or not member_id
            or len(member_id) > 128
        ):
            return _safe_error("INVALID_REPLAY_REQUEST", "Replay request is invalid.", 400)
        try:
            result = workflow_service.replay(member_id)
        except DemoRunError as error:
            return _safe_error("REPLAY_FAILED", str(error), 409)
        except Exception:
            return _safe_error("REPLAY_FAILED", "Replay could not be completed.", 500)
        return jsonify(_result_payload(result, index)), 201

    @app.get("/api/interventions")
    def interventions():
        active = workflow_service.list_active_interventions()
        active_ids = {item["intervention_id"] for item in active}
        historical = [
            item for item in index.list_interventions() if item["intervention_id"] not in active_ids
        ]
        return jsonify({"interventions": [*active, *historical]})

    @app.post("/api/interventions")
    def start_intervention():
        try:
            return jsonify(workflow_service.start_intervention()), 201
        except DemoRunError as error:
            return _safe_error("INTERVENTION_FAILED", str(error), 409)
        except Exception:
            return _safe_error(
                "INTERVENTION_FAILED",
                "Intervention could not be started.",
                500,
            )

    @app.get("/api/interventions/<intervention_id>")
    def intervention_detail(intervention_id: str):
        try:
            return jsonify(workflow_service.get_intervention(intervention_id))
        except OperatorConsoleError:
            try:
                return jsonify(index.get_intervention(intervention_id))
            except ProductArtifactError as error:
                return _safe_error("INTERVENTION_NOT_FOUND", str(error), 404)

    @app.get("/api/interventions/<intervention_id>/controls")
    def intervention_controls(intervention_id: str):
        try:
            return jsonify(workflow_service.get_controls(intervention_id))
        except OperatorConsoleError as error:
            return _operator_error(error)

    @app.get("/api/interventions/<intervention_id>/view")
    def intervention_view(intervention_id: str):
        try:
            content, mime_type = workflow_service.get_view(intervention_id)
        except OperatorConsoleError as error:
            return _operator_error(error)
        return Response(
            content,
            mimetype=mime_type,
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.post("/api/interventions/<intervention_id>/actions")
    def intervention_action(intervention_id: str):
        raw_payload: object = request.get_json(silent=True)
        if not isinstance(raw_payload, dict):
            return _safe_error("INVALID_REQUEST", "A JSON object is required.", 400)
        payload = cast(dict[str, object], raw_payload)
        try:
            submission = OperatorActionSubmission.model_validate(payload)
            return jsonify(workflow_service.execute_action(intervention_id, submission))
        except ValidationError:
            return _safe_error("INVALID_REQUEST", "Operator action is invalid.", 400)
        except OperatorConsoleError as error:
            return _operator_error(error)

    @app.post("/api/interventions/<intervention_id>/return-control")
    def return_control(intervention_id: str):
        try:
            return jsonify(workflow_service.return_control(intervention_id))
        except OperatorConsoleError as error:
            return _operator_error(error)
        except DemoRunError as error:
            return _safe_error("RESUME_FAILED", str(error), 409)

    @app.post("/api/interventions/<intervention_id>/stop")
    def stop_intervention(intervention_id: str):
        try:
            return jsonify(workflow_service.stop(intervention_id))
        except OperatorConsoleError as error:
            return _operator_error(error)

    @app.get("/")
    @app.get("/<path:path>")
    def frontend(path: str = "index.html"):
        if path.startswith("api/"):
            return _safe_error("RESOURCE_NOT_FOUND", "API resource was not found.", 404)
        if not web_root.is_dir():
            return _safe_error(
                "FRONTEND_NOT_BUILT",
                "Build the web client before starting the product server.",
                503,
            )
        requested = web_root / path
        if path and requested.is_file():
            return send_from_directory(web_root, path)
        return send_from_directory(web_root, "index.html")

    if isinstance(workflow_service, ProductWorkflowService):
        atexit.register(workflow_service.close)
    atexit.register(discovery_workspace.close)
    return app


def _result_payload(result: DemoRunResult, index: ProductArtifactIndex) -> dict[str, object]:
    run_id = str(result.summary["run_id"])
    return {"run": index.get_run(run_id), "events": index.list_events(run_id)}


def _load_environment(path: Path = PROJECT_ROOT / ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_file():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip('"').strip("'")
    values.update(os.environ)
    return values


def _operator_error(error: OperatorConsoleError) -> tuple[Response, int]:
    return _safe_error(error.code, error.summary, error.http_status)


def _safe_error(code: str, summary: str, status: int) -> tuple[Response, int]:
    return jsonify({"error": {"code": code, "summary": summary}}), status


def main(*, port: int = 5000) -> None:
    app = create_product_app()
    from .legacy_bank_b import create_app as create_second_app

    with serve_app(create_target_app(), port=5001), serve_app(create_second_app(), port=5002):
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
