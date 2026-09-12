"""Surface adapter protocol.

This is the architectural port between semantic workflow targets and a
concrete browser surface implementation. It intentionally contains no
Playwright imports or raw browser handles.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from capability_runner.contracts.actions import ActionSpec
from capability_runner.contracts.browser_discovery import BrowserObservation, InteractiveElement
from capability_runner.contracts.observations import ObservationSpec
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    SurfaceActionResult,
    SurfaceFailureEvidence,
    SurfaceSessionRef,
    TargetInspectionResult,
)


@runtime_checkable
class SurfaceAdapter(Protocol):
    async def open_surface_session(self, profile: ApplicationProfile) -> SurfaceSessionRef:
        """Open a new concrete surface session for the supplied application profile."""
        ...

    async def observe_surface(self, session: SurfaceSessionRef) -> ObservationSpec:
        """Observe the current surface state as typed contract data."""
        ...

    async def perform_action(
        self,
        session: SurfaceSessionRef,
        action: ActionSpec,
        binding: BrowserTargetBinding,
    ) -> SurfaceActionResult:
        """Perform one already-authorized action against a resolved binding."""
        ...

    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult:
        """Inspect one trusted semantic target without exposing a raw handle."""
        ...

    async def capture_failure_evidence(
        self,
        session: SurfaceSessionRef,
    ) -> SurfaceFailureEvidence | None:
        """Capture supported failure evidence without exposing raw browser handles."""
        ...

    async def close_surface_session(self, session: SurfaceSessionRef) -> None:
        """Release the concrete surface session resource."""
        ...


class BrowserObservationPort(Protocol):
    async def inspect_bound_element(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> InteractiveElement: ...

    async def observe_browser(self, session: SurfaceSessionRef) -> BrowserObservation: ...

    async def resolve_observed(
        self,
        session: SurfaceSessionRef,
        observation_id: str,
        element_ref: str,
    ) -> InteractiveElement: ...
