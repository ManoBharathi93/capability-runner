"""Local Flask interface for one same-session operator intervention."""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from pydantic import ValidationError

from capability_runner.application.operator_console import (
    OperatorConsoleError,
    OperatorConsoleService,
)
from capability_runner.contracts.operator_console import (
    OperatorActionResponse,
    OperatorActionSubmission,
    OperatorTransitionResponse,
)

from .async_core_runner import AsyncCoreRunner


def create_operator_console_app(
    *,
    console: OperatorConsoleService,
    async_runner: AsyncCoreRunner,
) -> Flask:
    app = Flask(__name__)

    @app.get("/operator/interventions/<intervention_id>")
    def operator_page(intervention_id: str):
        error = _ensure_known_intervention(console, async_runner, intervention_id)
        if error is not None:
            return error
        return render_template(
            "operator_intervention.html",
            intervention_id=intervention_id,
        )

    @app.get("/api/interventions/<intervention_id>")
    def intervention_status(intervention_id: str):
        try:
            status = async_runner.run(console.get_status(intervention_id))
        except OperatorConsoleError as error:
            return _error_response(error)
        return jsonify(status.model_dump(mode="json"))

    @app.get("/api/interventions/<intervention_id>/view")
    def intervention_view(intervention_id: str):
        try:
            view = async_runner.run(console.capture_view(intervention_id))
        except OperatorConsoleError as error:
            return _error_response(error)
        return Response(
            view.content,
            mimetype=view.mime_type,
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/api/interventions/<intervention_id>/controls")
    def intervention_controls(intervention_id: str):
        try:
            controls = async_runner.run(console.get_available_controls(intervention_id))
        except OperatorConsoleError as error:
            return _error_response(error)
        return jsonify({"controls": [control.model_dump(mode="json") for control in controls]})

    @app.post("/api/interventions/<intervention_id>/actions")
    def intervention_action(intervention_id: str):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _safe_error("INVALID_REQUEST", "A JSON object is required.", 400)
        try:
            submission = OperatorActionSubmission.model_validate(payload)
            result = async_runner.run(console.execute_action(intervention_id, submission))
        except ValidationError:
            return _safe_error("INVALID_REQUEST", "Operator action is invalid.", 400)
        except OperatorConsoleError as error:
            return _error_response(error)
        return jsonify(result.model_dump(mode="json")), _action_status(result)

    @app.post("/api/interventions/<intervention_id>/return-control")
    def return_control(intervention_id: str):
        try:
            result = async_runner.run(console.return_control(intervention_id))
        except OperatorConsoleError as error:
            return _error_response(error)
        return jsonify(result.model_dump(mode="json")), _transition_status(result)

    @app.post("/api/interventions/<intervention_id>/stop")
    def stop_intervention(intervention_id: str):
        try:
            result = async_runner.run(console.stop(intervention_id))
        except OperatorConsoleError as error:
            return _error_response(error)
        return jsonify(result.model_dump(mode="json")), _transition_status(result)

    return app


def _ensure_known_intervention(
    console: OperatorConsoleService,
    async_runner: AsyncCoreRunner,
    intervention_id: str,
) -> tuple[Response, int] | None:
    try:
        async_runner.run(console.get_status(intervention_id))
    except OperatorConsoleError as error:
        return _error_response(error)
    return None


def _action_status(result: OperatorActionResponse) -> int:
    if result.executed:
        return 200
    if result.reason_code in {"ACTION_DENIED", "POLICY_CONTEXT_DENIED"}:
        return 403
    if result.reason_code in {"TARGET_BINDING_NOT_FOUND", "TARGET_NOT_FOUND"}:
        return 422
    return 409


def _transition_status(result: OperatorTransitionResponse) -> int:
    if result.outcome in {"RESUME_VALIDATION_REQUIRED", "SESSION_STOPPED"}:
        return 200
    return 409


def _error_response(error: OperatorConsoleError) -> tuple[Response, int]:
    return _safe_error(error.code, error.summary, error.http_status)


def _safe_error(code: str, summary: str, status: int) -> tuple[Response, int]:
    payload: dict[str, Any] = {"error": {"code": code, "summary": summary}}
    return jsonify(payload), status
