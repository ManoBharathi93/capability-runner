from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

import pytest
from pydantic import SecretStr
from werkzeug.serving import make_server

from capability_runner.contracts.actions import (
    ClickAction,
    FillAction,
    NavigateAction,
    WaitAction,
)
from capability_runner.contracts.observations import OutcomeObservation, PageObservation
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    FrameContext,
    LabelLocator,
    RoleLocator,
    SemanticTargetRef,
    SurfaceSessionRef,
    TextLocator,
)
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.surfaces.browser_surface_adapter import (
    BrowserSurfaceAdapter,
    BrowserSurfaceSessionClosedError,
)
from demo_app.app import DemoScenario, create_app
from demo_app.fixtures import ScenarioMode
from tests.fixtures.corebank_browser_profile import build_core_bank_demo_profile

T = TypeVar("T")


def _run[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


@contextmanager
def serve_demo_app(
    *, mode: ScenarioMode = "normal", delay: float = 0.12
) -> Generator[str, None, None]:
    app = create_app(scenario=DemoScenario(mode=mode, search_delay_seconds=delay))
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _profile(base_url: str) -> ApplicationProfile:
    return build_core_bank_demo_profile(f"{base_url}/")


def _binding(profile: ApplicationProfile, target_value: str) -> BrowserTargetBinding:
    for binding in profile.target_bindings:
        if binding.semantic_target.value == target_value:
            return binding
    raise AssertionError(f"missing target {target_value}")


async def _open_session(
    base_url: str, *, profile: ApplicationProfile | None = None, timeout_ms: int = 2_000
) -> tuple[BrowserSurfaceAdapter, SurfaceSessionRef, ApplicationProfile]:
    adapter = BrowserSurfaceAdapter(headless=True, default_timeout_ms=timeout_ms)
    resolved_profile = profile or _profile(base_url)
    session = await adapter.open_surface_session(resolved_profile)
    return adapter, session, resolved_profile


def _demo_target(base_url: str) -> ProfileTarget:
    return ProfileTarget.model_validate(
        {
            "kind": "profile",
            "application": "corebank",
            "profile": "legacy-browser",
            "entry_url": f"{base_url}/",
        }
    )


def _search_input(profile: ApplicationProfile) -> BrowserTargetBinding:
    return _binding(profile, "member.search.member_id")


def _search_submit(profile: ApplicationProfile) -> BrowserTargetBinding:
    return _binding(profile, "member.search.submit")


def _results_open(profile: ApplicationProfile) -> BrowserTargetBinding:
    return _binding(profile, "member.results.open")


def _savings_open(profile: ApplicationProfile) -> BrowserTargetBinding:
    return _binding(profile, "member.accounts.savings")


def _account_close(profile: ApplicationProfile) -> BrowserTargetBinding:
    return _binding(profile, "member.account.close")


def test_browser_session_opens_real_local_demo_app() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> PageObservation:
            adapter, session, _ = await _open_session(base_url)
            try:
                observation = await adapter.observe_surface(session)
                assert isinstance(observation, PageObservation)
                return observation
            finally:
                await adapter.aclose()

        observation = _run(scenario())
        assert "Northstar Member Services" in observation.visible_text
        assert "Legacy work area" in observation.visible_text
        assert "Member Search" in observation.visible_text


def test_surface_session_ref_is_opaque_and_contexts_are_isolated() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> None:
            adapter, session_one, profile = await _open_session(base_url)
            session_two = await adapter.open_surface_session(profile)
            try:
                assert set(session_one.model_dump()) == {"surface_session_id", "surface_kind"}
                assert set(session_two.model_dump()) == {"surface_session_id", "surface_kind"}

                state_one = adapter._sessions[session_one.surface_session_id]  # pyright: ignore[reportPrivateUsage]
                state_two = adapter._sessions[session_two.surface_session_id]  # pyright: ignore[reportPrivateUsage]
                assert state_one.context is not state_two.context

                await state_one.page.evaluate("localStorage.setItem('session-marker', 'one')")
                stored = await state_two.page.evaluate("localStorage.getItem('session-marker')")
                assert stored is None
            finally:
                await adapter.aclose()

        _run(scenario())


def test_operator_view_is_bounded_ephemeral_and_rejects_closed_session(tmp_path: Path) -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> None:
            adapter, session, _ = await _open_session(base_url)
            try:
                view = await adapter.capture_view(session)

                assert view.surface_session == session
                assert view.mime_type == "image/png"
                assert view.content.startswith(b"\x89PNG\r\n\x1a\n")
                assert 0 < len(view.content) <= 2_000_000
                assert 0 < view.width <= 1600
                assert 0 < view.height <= 1200
                assert list(tmp_path.rglob("*")) == []

                await adapter.close_surface_session(session)
                with pytest.raises(BrowserSurfaceSessionClosedError):
                    await adapter.capture_view(session)
            finally:
                await adapter.aclose()

        _run(scenario())


def test_primary_demo_workflow_for_member_12345_reaches_correct_account_balance() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> tuple[str, str]:
            adapter, session, profile = await _open_session(base_url)
            try:
                demo_target = _demo_target(base_url)
                await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("12345")),
                    _search_input(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _search_submit(profile),
                )
                results = await adapter.observe_surface(session)
                assert isinstance(results, PageObservation)
                assert "Avery Morgan" in results.visible_text

                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _results_open(profile),
                )
                details = await adapter.observe_surface(session)
                assert isinstance(details, PageObservation)
                assert "Member Details" in details.visible_text
                assert "Avery Morgan" in details.visible_text

                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _savings_open(profile),
                )
                savings = await adapter.observe_surface(session)
                assert isinstance(savings, PageObservation)
                assert "$4,382.21" in savings.visible_text

                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _account_close(profile),
                )
                back = await adapter.observe_surface(session)
                assert isinstance(back, PageObservation)
                assert "Member Details" in back.visible_text
                return results.visible_text, savings.visible_text
            finally:
                await adapter.aclose()

        results_text, savings_text = _run(scenario())
        assert "12345" in results_text
        assert "$4,382.21" in savings_text


def test_secondary_demo_workflow_for_member_67890_uses_the_same_row_scoped_control() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> PageObservation:
            adapter, session, profile = await _open_session(base_url)
            try:
                demo_target = _demo_target(base_url)
                await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("67890")),
                    _search_input(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _search_submit(profile),
                )
                results = await adapter.observe_surface(session)
                assert isinstance(results, PageObservation)
                assert "Jordan Lee" in results.visible_text

                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _results_open(profile),
                )
                details = await adapter.observe_surface(session)
                assert isinstance(details, PageObservation)
                assert "Jordan Lee" in details.visible_text

                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _savings_open(profile),
                )
                savings = await adapter.observe_surface(session)
                assert isinstance(savings, PageObservation)
                assert "$987.65" in savings.visible_text
                return savings
            finally:
                await adapter.aclose()

        observation = _run(scenario())
        assert "$987.65" in observation.visible_text


def test_unknown_member_and_permission_denied_states_are_typed() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> tuple[OutcomeObservation, OutcomeObservation]:
            adapter, session, profile = await _open_session(base_url)
            try:
                demo_target = _demo_target(base_url)
                await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("00000")),
                    _search_input(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _search_submit(profile),
                )
                not_found = await adapter.observe_surface(session)
                assert isinstance(not_found, OutcomeObservation)
                assert not_found.outcome == "business_outcome"

                await adapter.close_surface_session(session)
                session = await adapter.open_surface_session(profile)

                await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("55555")),
                    _search_input(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _search_submit(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _results_open(profile),
                )
                denied = await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _savings_open(profile),
                )
                assert denied.outcome == "APPLIED"
                denied_observation = await adapter.observe_surface(session)
                assert isinstance(denied_observation, OutcomeObservation)
                assert denied_observation.summary == "Permission denied"
                return not_found, denied_observation
            finally:
                await adapter.aclose()

        not_found, denied = _run(scenario())
        assert not_found.summary == "Member not found"
        assert denied.summary == "Permission denied"


def test_session_expired_scenario_is_observable() -> None:
    with serve_demo_app(mode="session_expired") as base_url:

        async def scenario() -> OutcomeObservation:
            adapter, session, _ = await _open_session(base_url)
            try:
                observation = await adapter.observe_surface(session)
                assert isinstance(observation, OutcomeObservation)
                return observation
            finally:
                await adapter.aclose()

        observation = _run(scenario())
        assert observation.summary == "Session expired"


def test_navigation_and_wait_actions_are_supported() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> PageObservation:
            adapter, session, profile = await _open_session(base_url)
            try:
                navigation = await adapter.perform_action(
                    session,
                    NavigateAction.model_validate(
                        {"kind": "navigate", "url": f"{base_url}/workspace"}
                    ),
                    _search_input(profile),
                )
                assert navigation.outcome == "APPLIED"
                waited = await adapter.perform_action(
                    session,
                    WaitAction(seconds=0.01),
                    _search_submit(profile),
                )
                assert waited.outcome == "APPLIED"
                observation = await adapter.observe_surface(session)
                assert isinstance(observation, PageObservation)
                return observation
            finally:
                await adapter.aclose()

        observation = _run(scenario())
        assert "Search" in observation.visible_text


def test_ambiguous_primary_candidate_does_not_fall_back_to_the_first_match() -> None:
    with serve_demo_app() as base_url:
        extra_binding = BrowserTargetBinding(
            semantic_target=SemanticTargetRef(value="member.details.open_any"),
            frame=FrameContext(name="work-area"),
            locator_candidates=(
                RoleLocator(kind="role", role="link", name="Open", exact=True),
                TextLocator(kind="text", text="Open", exact=True),
            ),
        )
        base_profile = build_core_bank_demo_profile(f"{base_url}/")
        profile = base_profile.model_copy(
            update={"target_bindings": base_profile.target_bindings + (extra_binding,)}
        )

        async def scenario() -> str:
            adapter, session, _ = await _open_session(base_url, profile=profile)
            try:
                demo_target = _demo_target(base_url)
                await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("12345")),
                    _search_input(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _search_submit(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _results_open(profile),
                )
                result = await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=_demo_target(base_url), button="left"),
                    extra_binding,
                )
                return result.outcome
            finally:
                await adapter.aclose()

        assert _run(scenario()) == "TARGET_AMBIGUOUS"


def test_button_to_link_fallback_resolves_the_close_control() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> tuple[str, PageObservation]:
            adapter, session, profile = await _open_session(base_url)
            try:
                demo_target = _demo_target(base_url)
                await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("12345")),
                    _search_input(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _search_submit(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _results_open(profile),
                )
                await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _savings_open(profile),
                )
                result = await adapter.perform_action(
                    session,
                    ClickAction(kind="click", target=demo_target, button="left"),
                    _account_close(profile),
                )
                observation = await adapter.observe_surface(session)
                assert isinstance(observation, PageObservation)
                return result.outcome, observation
            finally:
                await adapter.aclose()

        outcome, observation = _run(scenario())
        assert outcome == "APPLIED"
        assert "Member Details" in observation.visible_text


def test_missing_frame_and_unknown_semantic_target_fail_cleanly() -> None:
    with serve_demo_app() as base_url:
        missing_frame_binding = BrowserTargetBinding(
            semantic_target=SemanticTargetRef(value="member.search.member_id"),
            frame=FrameContext(name="missing-frame"),
            locator_candidates=(
                RoleLocator(kind="role", role="textbox", name="Member ID", exact=True),
                LabelLocator(kind="label", label="Member ID", exact=True),
            ),
        )
        unknown_binding = BrowserTargetBinding(
            semantic_target=SemanticTargetRef(value="member.unknown.control"),
            frame=FrameContext(name="work-area"),
            locator_candidates=(
                RoleLocator(kind="role", role="textbox", name="Member ID", exact=True),
                LabelLocator(kind="label", label="Member ID", exact=True),
            ),
        )
        base_profile = build_core_bank_demo_profile(f"{base_url}/")
        profile = base_profile.model_copy(
            update={"target_bindings": base_profile.target_bindings + (missing_frame_binding,)}
        )

        async def scenario() -> tuple[str, str]:
            adapter, session, _ = await _open_session(base_url, profile=profile)
            try:
                demo_target = _demo_target(base_url)
                missing_frame = await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("12345")),
                    missing_frame_binding,
                )
                unknown_target = await adapter.perform_action(
                    session,
                    FillAction(kind="fill", target=demo_target, value=SecretStr("12345")),
                    unknown_binding,
                )
                return missing_frame.outcome, unknown_target.outcome
            finally:
                await adapter.aclose()

        missing_frame_outcome, unknown_target_outcome = _run(scenario())
        assert missing_frame_outcome == "TARGET_NOT_FOUND"
        assert unknown_target_outcome == "TARGET_NOT_FOUND"


def test_closing_a_surface_session_releases_it_and_shutdown_clears_outstanding_resources() -> None:
    with serve_demo_app() as base_url:

        async def scenario() -> None:
            adapter, session, profile = await _open_session(base_url)
            await adapter.open_surface_session(profile)
            await adapter.close_surface_session(session)
            try:
                    # pyright: ignore[reportPrivateUsage]
                with pytest.raises(BrowserSurfaceSessionClosedError):
                    await adapter.observe_surface(session)
                await adapter.aclose()
                assert adapter._sessions == {}  # pyright: ignore[reportPrivateUsage]
                assert adapter._browser is None  # pyright: ignore[reportPrivateUsage]
                assert adapter._playwright is None  # pyright: ignore[reportPrivateUsage]
            finally:
                # other is closed by aclose above if it succeeded; this keeps teardown safe.
                if adapter._browser is not None or adapter._playwright is not None:  # pyright: ignore[reportPrivateUsage]
                    await adapter.aclose()

        _run(scenario())
