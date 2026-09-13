"""Read-only projection of sanitized demo artifacts for the product frontend."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from capability_runner.capabilities.capability_validator import (
    CapabilityValidationError,
    CapabilityValidator,
)
from capability_runner.contracts.capabilities import CapabilityDefinition
from capability_runner.contracts.evidence import EvidenceEvent

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SUMMARY_FIELDS = frozenset(
    {
        "artifact_file",
        "balance_minor_units",
        "blocked_action",
        "automated_browser_action_count",
        "operator_gateway_action_count",
        "reason_code",
        "physical_human_acceptance",
        "browser_action_count",
        "builder_model_calls",
        "business_outcome",
        "capability_id",
        "capability_version",
        "currency",
        "demo_kind",
        "discovery_model_calls",
        "discovery_result",
        "failure_reason",
        "fresh_replay_session",
        "generation_after",
        "generation_before",
        "operator_mode",
        "outputs",
        "provider",
        "repeated_automation_side_effects",
        "replay_model_calls",
        "replay_result",
        "run_id",
        "same_surface_session",
        "schema_version",
        "status",
    }
)


class ProductArtifactError(LookupError):
    pass


class ProductArtifactIndex:
    def __init__(self, *, runtime_root: Path, curated_root: Path) -> None:
        self._runtime_root = runtime_root
        self._curated_root = curated_root

    def overview(self) -> dict[str, object]:
        capabilities = self.list_capabilities()
        runs = self.list_runs()
        interventions = self.list_interventions()
        verified_runs = sum(1 for run in runs if run.get("status") == "SUCCESS")
        return {
            "capability_count": len(capabilities),
            "run_count": len(runs),
            "active_run_count": 0,
            "intervention_count": len(interventions),
            "verified_run_count": verified_runs,
            "system_health": "UNAVAILABLE",
            "environment": "LOCAL_REVIEW",
            "recent_runs": runs[:5],
        }

    def list_capabilities(self) -> list[dict[str, object]]:
        indexed: dict[tuple[str, str], tuple[float, CapabilityDefinition]] = {}
        for path in self._capability_paths():
            try:
                definition = CapabilityDefinition.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
                CapabilityValidator().validate(definition)
            except (OSError, ValidationError, CapabilityValidationError):
                continue
            key = (definition.capability_id, definition.capability_version)
            modified = path.stat().st_mtime
            if key not in indexed or modified > indexed[key][0]:
                indexed[key] = (modified, definition)
        capabilities = [
            self._capability_dto(definition, modified) for modified, definition in indexed.values()
        ]
        return sorted(
            capabilities,
            key=lambda item: (str(item["name"]).casefold(), str(item["version"])),
        )

    def get_capability(
        self,
        capability_id: str,
        version: str | None = None,
    ) -> dict[str, object]:
        self._require_identifier(capability_id)
        if version is not None:
            self._require_identifier(version)
        matches = [
            capability
            for capability in self.list_capabilities()
            if capability["capability_id"] == capability_id
            and (version is None or capability["version"] == version)
        ]
        if not matches:
            raise ProductArtifactError("Capability was not found.")
        return max(matches, key=lambda item: self._version_key(str(item["version"])))

    def list_runs(self) -> list[dict[str, object]]:
        indexed: dict[str, tuple[float, dict[str, object]]] = {}
        for summary_path in self._summary_paths():
            summary = self._read_summary(summary_path)
            if summary is None:
                continue
            run_id = summary.get("run_id")
            if not isinstance(run_id, str) or not _IDENTIFIER.fullmatch(run_id):
                continue
            modified = summary_path.stat().st_mtime
            dto = {
                key: value
                for key, value in summary.items()
                if key in _SUMMARY_FIELDS and self._is_json_value(value)
            }
            dto["created_at"] = datetime.fromtimestamp(modified, UTC).isoformat()
            dto["event_count"] = len(self._read_events(summary_path.parent))
            existing = indexed.get(run_id)
            if existing is None or modified > existing[0]:
                indexed[run_id] = (modified, dto)
        ordered = sorted(indexed.values(), key=lambda item: item[0], reverse=True)
        return [item[1] for item in ordered]

    def get_run(self, run_id: str) -> dict[str, object]:
        self._require_identifier(run_id)
        for run in self.list_runs():
            if run["run_id"] == run_id:
                return run
        raise ProductArtifactError("Run was not found.")

    def list_events(self, run_id: str) -> list[dict[str, object]]:
        self._require_identifier(run_id)
        directory = self._run_directory(run_id)
        if directory is None:
            raise ProductArtifactError("Run was not found.")
        return [event.model_dump(mode="json") for event in self._read_events(directory)]

    def list_interventions(self) -> list[dict[str, object]]:
        interventions: list[dict[str, object]] = []
        for run in self.list_runs():
            if run.get("demo_kind") != "intervention":
                continue
            directory = self._run_directory(str(run["run_id"]))
            events = self._read_events(directory) if directory is not None else []
            context = next(
                (event for event in events if event.reason_code == "INTERVENTION_CONTEXT_RECORDED"),
                None,
            )
            raw_intervention_id: object = (
                context.metadata.get("intervention_id") if context is not None else None
            )
            interventions.append(
                {
                    "intervention_id": (
                        raw_intervention_id if isinstance(raw_intervention_id, str) else None
                    ),
                    "run_id": run["run_id"],
                    "capability_id": run.get("capability_id"),
                    "reason_code": run.get("reason_code", "APPROVAL_REQUIRED"),
                    "summary": "Operator approval was required for a trusted semantic action.",
                    "control_state": "terminal",
                    "state_label": str(run.get("status", "Completed intervention")),
                    "active": False,
                    "created_at": run["created_at"],
                    "blocked_action": run.get("blocked_action"),
                    "generation_before": run.get("generation_before"),
                    "generation_after": run.get("generation_after"),
                    "replay_result": run.get("replay_result"),
                }
            )
        return interventions

    def get_intervention(self, intervention_id: str) -> dict[str, object]:
        self._require_identifier(intervention_id)
        for intervention in self.list_interventions():
            if intervention["intervention_id"] == intervention_id:
                return intervention
        raise ProductArtifactError("Intervention was not found.")

    def _capability_paths(self) -> list[Path]:
        paths: list[Path] = []
        for root in (self._curated_root, self._runtime_root):
            if root.is_dir():
                paths.extend(root.glob("**/capabilities/*/*.json"))
        return paths

    def _summary_paths(self) -> list[Path]:
        paths: list[Path] = []
        for root in (self._curated_root, self._runtime_root):
            if root.is_dir():
                paths.extend(root.glob("*/summary.json"))
        return paths

    def _run_directory(self, run_id: str) -> Path | None:
        candidates = [
            summary.parent
            for summary in self._summary_paths()
            if self._read_summary(summary, expected_run_id=run_id) is not None
        ]
        return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None

    @staticmethod
    def _read_summary(
        path: Path,
        *,
        expected_run_id: str | None = None,
    ) -> dict[str, object] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict):
            return None
        summary = cast(dict[str, object], value)
        if expected_run_id is not None and summary.get("run_id") != expected_run_id:
            return None
        return summary

    @staticmethod
    def _read_events(directory: Path) -> list[EvidenceEvent]:
        path = directory / "evidence.jsonl"
        if not path.is_file():
            return []
        events: list[EvidenceEvent] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                events.append(EvidenceEvent.model_validate_json(line))
            except ValidationError:
                continue
        return events

    @staticmethod
    def _capability_dto(
        definition: CapabilityDefinition,
        modified: float,
    ) -> dict[str, object]:
        payload = definition.model_dump(mode="json")
        return {
            "capability_id": definition.capability_id,
            "version": definition.capability_version,
            "name": definition.name,
            "description": definition.description,
            "application": definition.application_requirement.application_family,
            "surface_kind": definition.application_requirement.surface_kind,
            "status": "READY",
            "input_count": len(definition.inputs),
            "output_count": len(definition.outputs),
            "step_count": len(definition.steps),
            "updated_at": datetime.fromtimestamp(modified, UTC).isoformat(),
            "definition": payload,
        }

    @staticmethod
    def _version_key(version: str) -> tuple[int, int, int]:
        major, minor, patch = version.split(".")
        return int(major), int(minor), int(patch)

    @staticmethod
    def _require_identifier(value: str) -> None:
        if not _IDENTIFIER.fullmatch(value):
            raise ProductArtifactError("Resource identifier is invalid.")

    @classmethod
    def _is_json_value(cls, value: Any) -> bool:
        if value is None or isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(cls._is_json_value(item) for item in cast(list[object], value))
        if isinstance(value, dict):
            return all(
                isinstance(key, str) and cls._is_json_value(item)
                for key, item in cast(dict[object, object], value).items()
            )
        return False
