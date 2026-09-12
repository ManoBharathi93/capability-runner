from __future__ import annotations

import asyncio

from capability_runner.contracts.actions import ActionSpec
from capability_runner.contracts.observations import ObservationSpec
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    SemanticTargetRef,
    SurfaceActionResult,
    SurfaceFailureEvidence,
    SurfaceSessionRef,
    TargetInspectionResult,
)
from capability_runner.discovery.snapshot_collector import DiscoverySnapshotCollector


class InspectionAdapter:
    async def open_surface_session(self, profile: ApplicationProfile) -> SurfaceSessionRef:
        raise NotImplementedError

    async def observe_surface(self, session: SurfaceSessionRef) -> ObservationSpec:
        raise NotImplementedError

    async def perform_action(
        self,
        session: SurfaceSessionRef,
        action: ActionSpec,
        binding: BrowserTargetBinding,
    ) -> SurfaceActionResult:
        raise NotImplementedError

    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult:
        outcome = (
            "TARGET_AMBIGUOUS"
            if binding.semantic_target.value == "member.account.close"
            else "VISIBLE"
        )
        return TargetInspectionResult(
            outcome=outcome,
            target=binding.semantic_target,
            text="safe value" if outcome == "VISIBLE" else None,
            summary="Inspected.",
        )

    async def capture_failure_evidence(
        self,
        session: SurfaceSessionRef,
    ) -> SurfaceFailureEvidence | None:
        return None

    async def close_surface_session(self, session: SurfaceSessionRef) -> None:
        return None


def test_discovery_collection_keeps_ambiguous_target_unavailable() -> None:
    profile = ApplicationProfile.model_validate(
        {
            "profile_id": "test",
            "application_family": "test",
            "variant": "test",
            "entry_point": "https://example.test/",
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value=target),
                    locator_candidates=(CssLocator(kind="css", selector=f"#{index}"),),
                )
                for index, target in enumerate(
                    ("member.details.identity", "member.account.close")
                )
            ],
        }
    )

    snapshot = asyncio.run(
        DiscoverySnapshotCollector(InspectionAdapter()).collect(
            SurfaceSessionRef(surface_session_id="surface"),
            profile,
            tuple(binding.semantic_target for binding in profile.target_bindings),
        )
    )

    states = {item.target.value: item.state for item in snapshot.observed_targets}
    assert states == {
        "member.details.identity": "VISIBLE",
        "member.account.close": "UNAVAILABLE",
    }