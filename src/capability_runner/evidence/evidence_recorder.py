from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from capability_runner.contracts.evidence import EvidenceEvent

from .redaction import RedactionContext, redact_event_payload

SAFE_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
EVIDENCE_FILE_NAME = "evidence.jsonl"


@dataclass(frozen=True, slots=True)
class EvidenceWriteResult:
    event_id: UUID
    path: Path


class EvidenceRecorder:
    def __init__(
        self,
        evidence_root: Path,
        run_id: str,
        *,
        redaction_context: RedactionContext | None = None,
    ) -> None:
        self._evidence_root = Path(evidence_root)
        self._run_id = self._validate_run_id(run_id)
        self._redaction_context = redaction_context or RedactionContext()

    @staticmethod
    def _validate_run_id(run_id: str) -> str:
        if not SAFE_RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("run_id must be a safe identifier")
        return run_id

    @property
    def run_directory(self) -> Path:
        return self._evidence_root / self._run_id

    @property
    def path(self) -> Path:
        return self.run_directory / EVIDENCE_FILE_NAME

    def record(
        self,
        event: EvidenceEvent,
        *,
        redaction_context: RedactionContext | None = None,
    ) -> EvidenceWriteResult:
        effective_context = redaction_context or self._redaction_context
        payload = event.model_dump(mode="python", exclude_none=True)
        sanitized_payload = redact_event_payload(payload, effective_context)
        line = json.dumps(sanitized_payload, ensure_ascii=False, separators=(",", ":"))

        self.run_directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{line}\n")

        return EvidenceWriteResult(event_id=event.event_id, path=self.path)
