"""Immutable local JSON storage for structurally validated capabilities."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from capability_runner.contracts.browser_discovery import CapabilityPackage
from capability_runner.contracts.capabilities import CapabilityDefinition

from .capability_validator import (
    CapabilityValidationError,
    CapabilityValidator,
    ValidatedCapability,
)


class CapabilityStoreError(RuntimeError):
    """Base error for capability persistence failures."""


class CapabilityVersionAlreadyExistsError(CapabilityStoreError):
    """Raised when an immutable capability version already exists."""


class CapabilityLoadError(CapabilityStoreError):
    """Raised when stored data cannot be parsed and structurally validated."""


class CapabilityStore:
    """Store each capability version as a reviewable immutable JSON file."""

    def __init__(self, root: Path, *, validator: CapabilityValidator | None = None) -> None:
        self._root = Path(root)
        self._validator = validator or CapabilityValidator()

    def save_package(self, package: CapabilityPackage) -> Path:
        self._validator.validate(package.capability)
        if package.profile.discovery_only or any(
            item.ephemeral_ref or item.observation_id for item in package.profile.target_bindings
        ):
            raise CapabilityStoreError("Ephemeral bindings cannot be stored.")
        path = self._path_for(
            package.capability.capability_id, package.capability.capability_version
        ).with_suffix(".package")
        path.mkdir(parents=True, exist_ok=False)
        capability_text = package.capability.model_dump_json(indent=2)
        profile_text = package.profile.model_dump_json(indent=2)
        (path / "capability.json").write_bytes(capability_text.encode("utf-8"))
        (path / "application-profile.json").write_bytes(profile_text.encode("utf-8"))
        metadata = package.model_dump(mode="json", exclude={"capability", "profile"})
        metadata["sha256"] = {
            "capability.json": hashlib.sha256(capability_text.encode()).hexdigest(),
            "application-profile.json": hashlib.sha256(profile_text.encode()).hexdigest(),
        }
        (path / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return path

    def load_package(self, capability_id: str, version: str) -> CapabilityPackage:
        path = self._path_for(capability_id, version).with_suffix(".package")
        metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        hashes = metadata.pop("sha256")
        for name in ("capability.json", "application-profile.json"):
            if hashlib.sha256((path / name).read_bytes()).hexdigest() != hashes[name]:
                raise CapabilityLoadError("Package integrity check failed.")
        package = CapabilityPackage.model_validate(
            {
                **metadata,
                "capability": json.loads((path / "capability.json").read_text(encoding="utf-8")),
                "profile": json.loads(
                    (path / "application-profile.json").read_text(encoding="utf-8")
                ),
            }
        )
        self._validator.validate(package.capability)
        return package

    def save(self, capability: ValidatedCapability) -> Path:
        definition = capability.definition
        destination = self._path_for(definition.capability_id, definition.capability_version)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise CapabilityVersionAlreadyExistsError(
                "capability version already exists: "
                f"{definition.capability_id} {definition.capability_version}"
            )

        payload = json.dumps(
            definition.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=destination.parent,
                prefix=f".{definition.capability_version}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                stream.write(f"{payload}\n")
                stream.flush()
                os.fsync(stream.fileno())
            if destination.exists():
                raise CapabilityVersionAlreadyExistsError(
                    "capability version already exists: "
                    f"{definition.capability_id} {definition.capability_version}"
                )
            os.replace(temporary_path, destination)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
        return destination

    def load(self, capability_id: str, capability_version: str) -> ValidatedCapability:
        destination = self._path_for(capability_id, capability_version)
        try:
            payload = json.loads(destination.read_text(encoding="utf-8"))
            definition = CapabilityDefinition.model_validate(payload)
            return self._validator.validate(definition)
        except (OSError, ValueError, ValidationError, CapabilityValidationError) as error:
            raise CapabilityLoadError(
                f"unable to load capability: {capability_id} {capability_version}"
            ) from error

    def list_versions(self, capability_id: str) -> tuple[str, ...]:
        capability_directory = (
            self._root
            / CapabilityDefinition.model_validate(
                {
                    "schema_version": 1,
                    "capability_id": capability_id,
                    "capability_version": "0.0.0",
                    "name": "validation",
                    "description": "validation",
                    "application_requirement": {
                        "application_family": "validation",
                        "surface_kind": "browser",
                    },
                }
            ).capability_id
        )
        if not capability_directory.exists():
            return ()
        versions = [path.stem for path in capability_directory.glob("*.json")]
        return tuple(sorted(versions, key=self._version_key))

    @staticmethod
    def _version_key(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.split("."))

    def _path_for(self, capability_id: str, capability_version: str) -> Path:
        definition = CapabilityDefinition.model_validate(
            {
                "schema_version": 1,
                "capability_id": capability_id,
                "capability_version": capability_version,
                "name": "validation",
                "description": "validation",
                "application_requirement": {
                    "application_family": "validation",
                    "surface_kind": "browser",
                },
            }
        )
        return self._root / definition.capability_id / f"{definition.capability_version}.json"
