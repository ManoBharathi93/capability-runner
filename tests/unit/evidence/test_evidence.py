from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import SecretStr, ValidationError

from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.evidence.redaction import RedactionContext, redact_value


def _read_evidence_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_writing_one_event_creates_valid_jsonl_under_root(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(tmp_path / "var" / "evidence", run_id="run-1")
    event = EvidenceEvent(
        event_type="lifecycle",
        component="engine",
        run_id="run-1",
        session_id="session-1",
        step_id="step-1",
        action_id="action-1",
        outcome="started",
        reason_code="STARTED",
        summary="Started run",
        metadata={"count": 1},
    )

    result = recorder.record(event)

    assert result.event_id == event.event_id
    assert result.path == recorder.path
    assert result.path.exists()
    lines = _read_evidence_lines(result.path)
    assert len(lines) == 1
    assert lines[0]["run_id"] == "run-1"
    assert lines[0]["session_id"] == "session-1"
    assert lines[0]["step_id"] == "step-1"
    assert lines[0]["action_id"] == "action-1"
    assert lines[0]["metadata"] == {"count": 1}
    assert isinstance(UUID(str(lines[0]["event_id"])), UUID)


def test_multiple_events_append_as_separate_json_objects(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(tmp_path / "var" / "evidence", run_id="run-1")

    recorder.record(
        EvidenceEvent(
            event_type="lifecycle",
            component="engine",
            run_id="run-1",
            summary="first",
        )
    )
    recorder.record(
        EvidenceEvent(
            event_type="outcome",
            component="engine",
            run_id="run-1",
            outcome="success",
            summary="second",
        )
    )

    lines = _read_evidence_lines(recorder.path)
    assert len(lines) == 2
    assert lines[0]["summary"] == "first"
    assert lines[1]["summary"] == "second"


def test_correlation_identifiers_survive_sanitization(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(
        tmp_path / "var" / "evidence",
        run_id="run-1",
        redaction_context=RedactionContext(explicit_values=frozenset({"MEMBER_PRIVATE_74291"})),
    )
    event = EvidenceEvent(
        event_type="action",
        component="engine",
        run_id="run-1",
        session_id="session-2",
        step_id="step-3",
        action_id="action-4",
        summary="Lookup MEMBER_PRIVATE_74291 failed",
    )

    recorder.record(event)
    payload = recorder.path.read_bytes()

    assert b"run-1" in payload
    assert b"session-2" in payload
    assert b"step-3" in payload
    assert b"action-4" in payload
    assert b"MEMBER_PRIVATE_74291" not in payload
    assert b"[REDACTED]" in payload


def test_secretstr_sentinel_never_appears_in_persisted_bytes(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(
        tmp_path / "var" / "evidence",
        run_id="run-1",
        redaction_context=RedactionContext(explicit_values=frozenset({"MEMBER_PRIVATE_74291"})),
    )
    event = EvidenceEvent(
        event_type="error",
        component="engine",
        run_id="run-1",
        summary="Lookup MEMBER_PRIVATE_74291 failed",
        metadata={"token": SecretStr("SUPER_SECRET_TOKEN_9F4A2")},
    )

    recorder.record(event)
    payload = recorder.path.read_bytes()

    assert b"SUPER_SECRET_TOKEN_9F4A2" not in payload
    assert b"MEMBER_PRIVATE_74291" not in payload
    assert b"[REDACTED]" in payload


def test_explicit_sensitive_values_are_redacted_in_nested_metadata_and_summaries(
    tmp_path: Path,
) -> None:
    recorder = EvidenceRecorder(
        tmp_path / "var" / "evidence",
        run_id="run-1",
        redaction_context=RedactionContext(explicit_values=frozenset({"MEMBER_PRIVATE_74291"})),
    )
    event = EvidenceEvent(
        event_type="error",
        component="engine",
        run_id="run-1",
        summary="Lookup MEMBER_PRIVATE_74291 failed",
        metadata={
            "details": {
                "message": "Lookup MEMBER_PRIVATE_74291 failed",
                "nested": ["prefix MEMBER_PRIVATE_74291 suffix"],
            }
        },
    )

    recorder.record(event)
    payload = recorder.path.read_text(encoding="utf-8")
    parsed = cast(dict[str, Any], json.loads(payload))
    metadata = cast(Mapping[str, Any], parsed["metadata"])
    details = cast(Mapping[str, Any], metadata["details"])
    nested = cast(list[Any], details["nested"])

    assert "MEMBER_PRIVATE_74291" not in payload
    assert parsed["summary"] == "Lookup [REDACTED] failed"
    assert details["message"] == "Lookup [REDACTED] failed"
    assert nested[0] == "prefix [REDACTED] suffix"


def test_sensitive_keys_are_redacted_and_safe_metadata_remains_intact(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(tmp_path / "var" / "evidence", run_id="run-1")
    event = EvidenceEvent(
        event_type="policy",
        component="engine",
        run_id="run-1",
        metadata={
            "password": "alpha",
            "passwd": "beta",
            "secret": "gamma",
            "token": "delta",
            "api_key": "epsilon",
            "authorization": "zeta",
            "cookie": "eta",
            "set_cookie": "theta",
            "count": 2,
            "notes": ["safe", {"nested": True}],
        },
    )

    recorder.record(event)
    parsed = _read_evidence_lines(recorder.path)[0]

    metadata = cast(Mapping[str, Any], parsed["metadata"])
    assert metadata["password"] == "[REDACTED]"
    assert metadata["passwd"] == "[REDACTED]"
    assert metadata["secret"] == "[REDACTED]"
    assert metadata["token"] == "[REDACTED]"
    assert metadata["api_key"] == "[REDACTED]"
    assert metadata["authorization"] == "[REDACTED]"
    assert metadata["cookie"] == "[REDACTED]"
    assert metadata["set_cookie"] == "[REDACTED]"
    assert metadata["count"] == 2
    notes = cast(list[Any], metadata["notes"])
    assert notes[0] == "safe"
    assert notes[1] == {"nested": True}


def test_unsupported_python_objects_are_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceEvent(
            event_type="error",
            component="engine",
            run_id="run-1",
            metadata={"unsupported": object()},
        )


def test_overlong_summaries_are_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceEvent(
            event_type="error",
            component="engine",
            run_id="run-1",
            summary="x" * 513,
        )


def test_path_traversal_run_id_cannot_escape_evidence_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        EvidenceRecorder(tmp_path / "var" / "evidence", run_id="../../secret")


def test_import_has_no_filesystem_side_effects(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, "-c", "import capability_runner.evidence"],
        check=True,
        cwd=tmp_path,
    )
    assert list(tmp_path.iterdir()) == []


def test_validation_error_object_is_redacted_before_persistence(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(
        tmp_path / "var" / "evidence",
        run_id="run-1",
        redaction_context=RedactionContext(explicit_values=frozenset({"MEMBER_PRIVATE_74291"})),
    )
    event = EvidenceEvent(
        event_type="error",
        component="engine",
        run_id="run-1",
        summary="Validation failed for MEMBER_PRIVATE_74291",
        metadata={"error": {"message": "Validation failed for MEMBER_PRIVATE_74291"}},
    )

    recorder.record(event)
    payload = recorder.path.read_bytes()

    assert b"MEMBER_PRIVATE_74291" not in payload
    assert b"Validation failed for [REDACTED]" in payload


def test_redact_value_replaces_sensitive_wrapper_values() -> None:
    redacted = redact_value(
        SecretStr("SUPER_SECRET_TOKEN_9F4A2"),
        RedactionContext(),
    )

    assert redacted == "[REDACTED]"
