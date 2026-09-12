"""Collect discovery snapshots across the trusted semantic target vocabulary."""

from __future__ import annotations

from capability_runner.contracts.evaluation import EvaluationSnapshot, TargetObservation
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    SemanticTargetRef,
    SurfaceSessionRef,
)
from capability_runner.surfaces.surface_adapter import SurfaceAdapter


class DiscoverySnapshotCollector:
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
                observations.append(TargetObservation(target=target, state="UNAVAILABLE"))
                continue
            try:
                inspected = await self._surface_adapter.inspect_target(session, binding)
            except Exception:
                observations.append(TargetObservation(target=target, state="UNAVAILABLE"))
                continue
            state = inspected.outcome
            if state == "TARGET_AMBIGUOUS":
                state = "UNAVAILABLE"
            observations.append(
                TargetObservation(
                    target=target,
                    state=state,
                    text=inspected.text if state == "VISIBLE" else None,
                )
            )
        return EvaluationSnapshot(observed_targets=tuple(observations))
