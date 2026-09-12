from __future__ import annotations

import asyncio

import pytest

from capability_runner.contracts.surfaces import ApplicationProfile
from capability_runner.surfaces.browser_surface_adapter import (
    BrowserSurfaceAdapter,
    BrowserSurfaceError,
)
from demo_app.legacy_bank_b import create_app
from demo_app.reviewer_runtime import serve_app


def test_unprofiled_snapshot_is_bounded_visible_and_refs_expire() -> None:
    with serve_app(create_app()) as url:

        async def check() -> None:
            adapter = BrowserSurfaceAdapter(default_timeout_ms=10_000)
            profile = ApplicationProfile.model_validate(
                {
                    "profile_id": "new",
                    "application_family": "new",
                    "variant": "unprofiled",
                    "entry_point": url,
                    "discovery_only": True,
                }
            )
            try:
                session = await adapter.open_surface_session(profile)
                first = await adapter.observe_browser(session)
                assert not profile.target_bindings
                assert 1 <= len(first.elements) <= 64
                control = next(item for item in first.elements if item.action_kind == "fill")
                assert control.label == "Customer reference"
                assert control.current_value_state == "empty"
                assert control.match_count == 1
                await adapter.resolve_observed(session, first.observation_id, control.ephemeral_ref)
                await adapter.capture_view(session)
                await adapter.resolve_observed(session, first.observation_id, control.ephemeral_ref)
                second = await adapter.observe_browser(session)
                assert first.observation_id != second.observation_id
                with pytest.raises(BrowserSurfaceError, match="STALE_ELEMENT_REF"):
                    await adapter.resolve_observed(
                        session, first.observation_id, control.ephemeral_ref
                    )
                state = adapter._sessions[session.surface_session_id]  # pyright: ignore[reportPrivateUsage]
                await state.page.evaluate(
                    "document.querySelector('input').replaceWith(document.createElement('input'))"
                )
                with pytest.raises(BrowserSurfaceError, match="STALE_ELEMENT_REF"):
                    await adapter.resolve_observed(
                        session, second.observation_id, second.elements[0].ephemeral_ref
                    )
                await state.page.evaluate("""() => {
                    document.body.innerHTML = '<button>Search</button><button>Search</button>'
                      + '<button hidden>Invisible secret</button>'
                      + '<script>secretScriptCanary</scr'+'ipt>';
                }""")
                duplicated = await adapter.observe_browser(session)
                assert len(duplicated.elements) == 2
                assert all(item.match_count == 2 for item in duplicated.elements)
                assert "Invisible secret" not in duplicated.model_dump_json()
                assert "secretScriptCanary" not in duplicated.model_dump_json()
                with pytest.raises(BrowserSurfaceError, match="TARGET_AMBIGUOUS"):
                    await adapter.resolve_observed(
                        session, duplicated.observation_id, duplicated.elements[0].ephemeral_ref
                    )
            finally:
                await adapter.aclose()

        asyncio.run(check())
