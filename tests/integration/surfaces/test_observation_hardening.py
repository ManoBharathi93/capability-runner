from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from capability_runner.contracts.actions import ClickAction
from capability_runner.contracts.browser_discovery import BrowserObservation, BrowserScope
from capability_runner.contracts.gateway import GatewayActionRequest, GatewayExecutionContext
from capability_runner.contracts.policy import PolicyDefinition
from capability_runner.contracts.surfaces import ApplicationProfile, SemanticTargetRef
from capability_runner.contracts.targets import UrlTarget
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.surfaces.browser_surface_adapter import (
    BrowserSurfaceAdapter,
    BrowserSurfaceError,
)
from demo_app.app import create_app
from demo_app.reviewer_runtime import serve_app


def profile_for(url: str) -> ApplicationProfile:
    return ApplicationProfile.model_validate(
        {
            "profile_id": "observations",
            "application_family": "observations",
            "variant": "unprofiled",
            "entry_point": url,
            "discovery_only": True,
        }
    )


def test_generation_session_frame_and_navigation_reject_before_dispatch(tmp_path: Path) -> None:
    with serve_app(create_app()) as url:

        async def check() -> None:
            adapter = BrowserSurfaceAdapter(default_timeout_ms=10_000)
            profile = profile_for(url)
            try:
                session = await adapter.open_surface_session(profile)
                first = await adapter.observe_browser(session)
                control = next(item for item in first.elements if item.action_kind == "fill")
                assert control.frame_identity == "work-area"
                assert control.perception_sources == ("html", "dom")
                assert control.binding is not None and control.binding.frame is not None
                await adapter.resolve_observed(session, first.observation_id, control.ephemeral_ref)
                second = await adapter.observe_browser(session)
                assert second.generation == first.generation + 1
                assert first.elements[0].ephemeral_ref == "1:e1"
                assert second.elements[0].ephemeral_ref == "2:e1"
                assert second.observation_fingerprint == first.observation_fingerprint
                assert second.change_summary and not second.change_summary.meaningful_change
                other = await adapter.open_surface_session(profile)
                other_observation = await adapter.observe_browser(other)
                assert other_observation.elements[0].ephemeral_ref == "1:e1"

                controller = SessionController()
                await controller.open_session(session_id="control", run_id="generation")
                gateway = ActionGateway(
                    policy_guard=PolicyGuard(PolicyDefinition(policy_id="deny", version="1")),
                    session_controller=controller,
                    surface_adapter=adapter,
                    observation_adapter=adapter,
                    browser_scope=BrowserScope(
                        origin=url.rstrip("/"),
                        read_only_paths=("/",),
                        read_only_post_paths=("/members/search",),
                    ),
                    evidence_recorder=EvidenceRecorder(tmp_path, "generation"),
                )
                context = GatewayExecutionContext(
                    run_id="generation",
                    control_session_id="control",
                    expected_generation=0,
                    surface_session=session,
                    profile=profile,
                )
                request = GatewayActionRequest(
                    action_id="stale",
                    step_id="stale",
                    semantic_target=SemanticTargetRef(value="page.button.search"),
                    action=ClickAction(target=UrlTarget(url=profile.entry_point)),
                )
                with (
                    patch.object(adapter, "_resolve_scope", new_callable=AsyncMock) as lookup,
                    patch.object(adapter, "perform_action", new_callable=AsyncMock) as dispatch,
                ):
                    # Even a current UUID cannot reinterpret an old generation's local e1.
                    for observation_id, ref, reason in (
                        (
                            first.observation_id,
                            first.elements[0].ephemeral_ref,
                            "STALE_ELEMENT_REF",
                        ),
                        (second.observation_id, "1:e1", "STALE_ELEMENT_REF"),
                        (second.observation_id, "2:e999", "UNKNOWN_ELEMENT_REF"),
                        (second.observation_id, "99:e999", "UNKNOWN_ELEMENT_REF"),
                        (second.observation_id, "e1", "STALE_ELEMENT_REF"),
                        (other_observation.observation_id, "1:e1", "STALE_ELEMENT_REF"),
                    ):
                        result = await gateway.execute_observed(
                            request,
                            context,
                            observation_id=observation_id,
                            element_ref=ref,
                        )
                        assert result.reason_code == reason
                        assert result.outcome == "FAILED"
                    lookup.assert_not_called()
                    dispatch.assert_not_called()

                state = adapter._sessions[session.surface_session_id]  # pyright: ignore[reportPrivateUsage]
                frame = state.page.frame(name="work-area")
                assert frame is not None
                # No DOM event: direct property mutation must still invalidate refs.
                await frame.locator("input").evaluate("el => el.value = '67890'")
                with patch.object(adapter, "_resolve_scope", new_callable=AsyncMock) as lookup:
                    with pytest.raises(BrowserSurfaceError, match="STALE_ELEMENT_REF"):
                        await adapter.resolve_observed(
                            session,
                            second.observation_id,
                            second.elements[0].ephemeral_ref,
                        )
                    lookup.assert_not_called()
                filled = await adapter.observe_browser(session)
                assert filled.change_summary and filled.change_summary.changed_count >= 1
                assert filled.observation_fingerprint != second.observation_fingerprint

                async def click(
                    observation: BrowserObservation, name: str, nearby: str = ""
                ) -> None:
                    selected = next(
                        item
                        for item in observation.elements
                        if item.accessible_name == name and nearby in item.nearby_text_summary
                    )
                    assert selected.binding is not None
                    result = await gateway.execute_observed(
                        request.model_copy(
                            update={
                                "action_id": f"click-{observation.generation}",
                                "semantic_target": selected.binding.semantic_target,
                            }
                        ),
                        context,
                        observation_id=observation.observation_id,
                        element_ref=selected.ephemeral_ref,
                    )
                    assert result.outcome == "EXECUTED", result.reason_code

                await click(filled, "Search")
                with patch.object(adapter, "_resolve_scope", new_callable=AsyncMock) as lookup:
                    with pytest.raises(BrowserSurfaceError, match="STALE_ELEMENT_REF"):
                        await adapter.resolve_observed(
                            session,
                            filled.observation_id,
                            filled.elements[0].ephemeral_ref,
                        )
                    lookup.assert_not_called()
                results = await adapter.observe_browser(session)
                assert results.change_summary and results.change_summary.meaningful_change
                assert results.change_summary.added_count > 0
                assert "Search Results" in results.headings
                await click(results, "Open")
                details = await adapter.observe_browser(session)
                assert details.change_summary and details.change_summary.meaningful_change
                assert details.change_summary.headings_changed
                opens = [item for item in details.elements if item.accessible_name == "Open"]
                assert len(opens) == 2
                assert all(item.match_count == 1 for item in opens)
                assert {item.structural_context for item in opens} == {
                    "row: Savings Open Open",
                    "row: Checking Open Open",
                }
                for item in opens:
                    await adapter.resolve_observed(
                        session, details.observation_id, item.ephemeral_ref
                    )
                await click(details, "Open", "Savings")
                account = await adapter.observe_browser(session)
                assert account.change_summary and account.change_summary.meaningful_change
                assert account.change_summary.removed_count > 0
                assert account.change_summary.added_count > 0
                await state.page.goto(url)
                with pytest.raises(BrowserSurfaceError, match="STALE_ELEMENT_REF"):
                    await adapter.resolve_observed(
                        session,
                        account.observation_id,
                        account.elements[0].ephemeral_ref,
                    )
            finally:
                await adapter.aclose()

        asyncio.run(check())


def test_accessible_native_dom_sources_and_privacy_bounds() -> None:
    with serve_app(create_app()) as url:

        async def check() -> None:
            adapter = BrowserSurfaceAdapter(default_timeout_ms=10_000)
            try:
                session = await adapter.open_surface_session(profile_for(url))
                state = adapter._sessions[session.surface_session_id]  # pyright: ignore[reportPrivateUsage]
                await state.page.set_content("""
                    <h1>Fixture</h1><span id="first">Customer</span>
                    <span id="second">reference</span>
                    <form aria-label="Find records">
                      <input aria-labelledby="first second" name="ref">
                      <label for="query">Query</label><input id="query">
                      <input type="submit" value="Search">
                      <label for="pw">Password</label>
                      <input id="pw" type="password" value="pwCanary">
                      <input autocomplete="one-time-code" value="otpCanary">
                    </form>
                    <p><strong>Total</strong> <span>42<span hidden>hiddenCanary</span></span></p>
                    <button aria-label="Inspect"><span hidden>hiddenNameCanary</span></button>
                    <button disabled>Disabled</button><button hidden>Hidden control</button>
                    <script>/* scriptCanary */</script><style>/* styleCanary */</style>
                    <div aria-hidden="true">
                      <p><strong>Hidden</strong><span>hiddenCanary</span></p>
                    </div>
                """)
                observation = await adapter.observe_browser(session)
                by_name = {item.accessible_name: item for item in observation.elements}
                assert by_name["Customer reference"].perception_sources == ("aria", "html", "dom")
                assert by_name["Query"].label == "Query"
                assert by_name["Search"].role == "button"
                assert by_name["Search"].match_count == 1
                assert by_name["Inspect"].perception_sources == ("aria", "html")
                assert by_name["Total"].text == "42"
                assert not by_name["Disabled"].enabled
                assert by_name["Query"].structural_context == "form: Find records"
                serialized = observation.model_dump_json()
                assert "Canary" not in serialized
                assert all(
                    "vision" not in source
                    for item in observation.elements
                    for source in item.perception_sources
                )
                await state.page.evaluate("""() => {
                    document.body.innerHTML = Array.from({length: 100}, (_, i) =>
                      '<p><strong>Field '+i+'</strong><span>'+ 'x'.repeat(300)+'</span></p>'
                    ).join('') + '<h2>'+ 'z'.repeat(200)+'</h2>';
                }""")
                bounded = await adapter.observe_browser(session)
                assert bounded.truncated
                assert len(bounded.elements) <= 64
                assert len(bounded.model_dump_json().encode()) <= 65536
                assert len(bounded.headings[0]) == 160
                assert (
                    sum(
                        len(getattr(item, field))
                        for item in bounded.elements
                        for field in (
                            "accessible_name",
                            "label",
                            "text",
                            "nearby_text_summary",
                            "structural_context",
                        )
                    )
                    <= 8192
                )
                assert all(len(item.nearby_text_summary) <= 200 for item in bounded.elements)
                again = await adapter.observe_browser(session)
                assert again.observation_fingerprint == bounded.observation_fingerprint
                assert again.change_summary and not again.change_summary.meaningful_change
            finally:
                await adapter.aclose()

        asyncio.run(check())
