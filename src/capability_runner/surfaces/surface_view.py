"""Read-only visual surface port for ephemeral operator presentation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from capability_runner.contracts.surfaces import SurfaceSessionRef, SurfaceView


@runtime_checkable
class SurfaceViewProvider(Protocol):
    async def capture_view(self, session: SurfaceSessionRef) -> SurfaceView:
        """Capture a bounded in-memory view without persisting an attachment."""
        ...
