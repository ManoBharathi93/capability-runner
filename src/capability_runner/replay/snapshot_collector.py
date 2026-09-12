"""Collect bounded semantic snapshots through the surface abstraction."""

from __future__ import annotations

from capability_runner.contracts.evaluation import (
    EvaluationSnapshot,
    TargetObservation,
)
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    SemanticTargetRef,
    SurfaceSessionRef,
)
from capability_runner.surfaces.surface_adapter import SurfaceAdapter


class SnapshotCollectionError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


class SnapshotCollector:
    def __init__(self, surface_adapter: SurfaceAdapter) -> None:
        self._surface_adapter = surface_adapter

    async def collect(
        self,
        session: SurfaceSessionRef,
        profile: ApplicationProfile,
        targets: tuple[SemanticTargetRef, ...],
    ) -> EvaluationSnapshot:
        bindings = {item.semantic_target.value: item for item in profile.target_bindings}
        observations: list[TargetObservation] = []
        for target in targets:
            binding = bindings.get(target.value)
            if binding is None:
                raise SnapshotCollectionError(
                    "TARGET_BINDING_MISSING",
                    "Trusted target binding is missing.",
                )
            inspected = await self._surface_adapter.inspect_target(session, binding)
            if inspected.outcome == "TARGET_AMBIGUOUS":
                raise SnapshotCollectionError("TARGET_AMBIGUOUS", "Target inspection is ambiguous.")
            observations.append(
                TargetObservation(
                    target=target,
                    state=inspected.outcome,
                    text=inspected.text,
                )
            )
        return EvaluationSnapshot(observed_targets=tuple(observations))
