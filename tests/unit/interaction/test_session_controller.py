from __future__ import annotations

import asyncio

import pytest

from capability_runner.contracts.sessions import SessionControllerError
from capability_runner.interaction.session_controller import SessionController


def _error_code(exc: SessionControllerError) -> str:
    return exc.code


async def _open_controller() -> SessionController:
    controller = SessionController()
    await controller.open_session(session_id="session-1", run_id="run-1")
    return controller


def test_new_session_starts_automation_owned() -> None:
    async def scenario() -> None:
        controller = SessionController()
        state = await controller.open_session(session_id="session-1", run_id="run-1")

        assert state.control_state == "automation_controlled"
        assert state.owner.kind == "automation"
        assert state.control_generation == 0

    asyncio.run(scenario())


def test_valid_automation_dispatch_is_admitted() -> None:
    async def scenario() -> None:
        controller = await _open_controller()

        async with controller.automation_dispatch("session-1", expected_generation=0) as state:
            assert state.control_state == "automation_controlled"
            assert state.control_generation == 0

    asyncio.run(scenario())


def test_stale_generation_is_rejected() -> None:
    async def scenario() -> None:
        controller = await _open_controller()

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("session-1", expected_generation=1):
                pass

        assert _error_code(exc_info.value) == "STALE_GENERATION"

    asyncio.run(scenario())


def test_dispatch_when_human_owns_session_is_rejected() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("session-1", expected_generation=2):
                pass

        assert _error_code(exc_info.value) == "DISPATCH_NOT_ALLOWED"

    asyncio.run(scenario())


def test_operator_dispatch_requires_operator_ownership() -> None:
    async def scenario() -> None:
        controller = await _open_controller()

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.operator_dispatch(
                "session-1",
                expected_generation=0,
                operator_id="op-1",
            ):
                pass

        assert _error_code(exc_info.value) == "DISPATCH_NOT_ALLOWED"

    asyncio.run(scenario())


def test_operator_dispatch_is_admitted_only_for_current_operator() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        state = await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.operator_dispatch(
                "session-1",
                expected_generation=state.control_generation,
                operator_id="op-2",
            ):
                pass
        assert _error_code(exc_info.value) == "NOT_OPERATOR_OWNER"

        async with controller.operator_dispatch(
            "session-1",
            expected_generation=state.control_generation,
            operator_id="op-1",
        ) as dispatch_state:
            assert dispatch_state == state

    asyncio.run(scenario())


def test_dispatch_in_resume_check_is_rejected() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        await controller.return_control_for_resume_check("session-1")

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("session-1", expected_generation=2):
                pass

        assert _error_code(exc_info.value) == "DISPATCH_NOT_ALLOWED"

    asyncio.run(scenario())


def test_dispatch_on_stopped_session_is_rejected() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.stop_session("session-1")

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("session-1", expected_generation=1):
                pass

        assert _error_code(exc_info.value) == "SESSION_STOPPED"

    asyncio.run(scenario())


def test_one_session_serializes_two_automated_side_effects() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        first_entered = asyncio.Event()
        release_first = asyncio.Event()
        second_entered = asyncio.Event()

        async def first_action() -> None:
            async with controller.automation_dispatch("session-1", expected_generation=0):
                first_entered.set()
                await release_first.wait()

        async def second_action() -> None:
            async with controller.automation_dispatch("session-1", expected_generation=0):
                second_entered.set()

        first_task = asyncio.create_task(first_action())
        await first_entered.wait()
        second_task = asyncio.create_task(second_action())
        await asyncio.sleep(0)
        assert not second_entered.is_set()
        release_first.set()
        await first_task
        await second_entered.wait()
        await second_task

    asyncio.run(scenario())


def test_separate_sessions_dispatch_independently() -> None:
    async def scenario() -> None:
        controller = SessionController()
        await controller.open_session(session_id="session-1", run_id="run-1")
        await controller.open_session(session_id="session-2", run_id="run-2")
        first_entered = asyncio.Event()
        release_first = asyncio.Event()
        second_entered = asyncio.Event()

        async def first_action() -> None:
            async with controller.automation_dispatch("session-1", expected_generation=0):
                first_entered.set()
                await release_first.wait()

        async def second_action() -> None:
            async with controller.automation_dispatch("session-2", expected_generation=0):
                second_entered.set()

        first_task = asyncio.create_task(first_action())
        await first_entered.wait()
        second_task = asyncio.create_task(second_action())
        await second_entered.wait()
        release_first.set()
        await first_task
        await second_task

    asyncio.run(scenario())


def test_pause_without_inflight_blocks_subsequent_automation() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("session-1", expected_generation=1):
                pass

        assert _error_code(exc_info.value) == "DISPATCH_NOT_ALLOWED"

    asyncio.run(scenario())


def test_human_takeover_cannot_preempt_in_flight_dispatch() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        first_entered = asyncio.Event()
        release_first = asyncio.Event()

        async def first_action() -> None:
            async with controller.automation_dispatch("session-1", expected_generation=0):
                first_entered.set()
                await release_first.wait()

        first_task = asyncio.create_task(first_action())
        await first_entered.wait()
        await controller.request_pause("session-1")

        with pytest.raises(SessionControllerError) as exc_info:
            await controller.grant_human_control(
                "session-1",
                operator_id="op-1",
                display_name="Alex",
            )

        assert _error_code(exc_info.value) == "ACTION_IN_FLIGHT"
        release_first.set()
        await first_task
        state = await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        assert state.control_state == "operator_controlled"

    asyncio.run(scenario())


def test_generation_changes_on_control_boundaries() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        assert (await controller.get_session("session-1")).control_generation == 0
        await controller.request_pause("session-1")
        assert (await controller.get_session("session-1")).control_generation == 1
        await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        assert (await controller.get_session("session-1")).control_generation == 2
        await controller.return_control_for_resume_check("session-1")
        assert (await controller.get_session("session-1")).control_generation == 2
        await controller.resume_automation_after_validation("session-1")
        assert (await controller.get_session("session-1")).control_generation == 3

    asyncio.run(scenario())


def test_human_return_produces_resume_check() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        state = await controller.return_control_for_resume_check("session-1")
        assert state.control_state == "resume_requested"

    asyncio.run(scenario())


def test_human_return_rejects_operator_action_in_flight() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        state = await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        entered = asyncio.Event()
        release = asyncio.Event()

        async def operator_action() -> None:
            async with controller.operator_dispatch(
                "session-1",
                expected_generation=state.control_generation,
                operator_id="op-1",
            ):
                entered.set()
                await release.wait()

        task = asyncio.create_task(operator_action())
        await entered.wait()

        with pytest.raises(SessionControllerError) as exc_info:
            await controller.return_control_for_resume_check("session-1")
        assert _error_code(exc_info.value) == "ACTION_IN_FLIGHT"

        release.set()
        await task
        returned = await controller.return_control_for_resume_check("session-1")
        assert returned.control_state == "resume_requested"

    asyncio.run(scenario())


def test_automation_remains_blocked_during_resume_check() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        await controller.return_control_for_resume_check("session-1")

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("session-1", expected_generation=2):
                pass

        assert _error_code(exc_info.value) == "DISPATCH_NOT_ALLOWED"

    asyncio.run(scenario())


def test_validated_resume_returns_automation_control() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        await controller.return_control_for_resume_check("session-1")
        state = await controller.resume_automation_after_validation("session-1")
        assert state.control_state == "automation_controlled"
        assert state.owner.kind == "automation"
        assert state.owner.run_id == "run-1"

    asyncio.run(scenario())


def test_old_generation_remains_invalid_after_resume() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        await controller.request_pause("session-1")
        await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        await controller.return_control_for_resume_check("session-1")
        await controller.resume_automation_after_validation("session-1")

        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("session-1", expected_generation=0):
                pass

        assert _error_code(exc_info.value) == "STALE_GENERATION"

    asyncio.run(scenario())


def test_exception_inside_dispatch_releases_slot() -> None:
    async def scenario() -> None:
        controller = await _open_controller()

        async def failing_action() -> None:
            async with controller.automation_dispatch("session-1", expected_generation=0):
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await failing_action()

        async with controller.automation_dispatch("session-1", expected_generation=0):
            pass

    asyncio.run(scenario())


def test_cancellation_inside_dispatch_releases_slot() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        started = asyncio.Event()
        release = asyncio.Event()

        async def cancellable_action() -> None:
            async with controller.automation_dispatch("session-1", expected_generation=0):
                started.set()
                await release.wait()

        task = asyncio.create_task(cancellable_action())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        async with controller.automation_dispatch("session-1", expected_generation=0):
            pass

    asyncio.run(scenario())


def test_invalid_state_transitions_fail_without_partial_mutation() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        before = await controller.get_session("session-1")

        with pytest.raises(SessionControllerError) as exc_info:
            await controller.grant_human_control(
                "session-1",
                operator_id="op-1",
                display_name="Alex",
            )

        after = await controller.get_session("session-1")
        assert _error_code(exc_info.value) == "INVALID_STATE_TRANSITION"
        assert after == before

    asyncio.run(scenario())


def test_repeated_pause_and_transfer_calls_are_deterministic() -> None:
    async def scenario() -> None:
        controller = await _open_controller()
        first_pause = await controller.request_pause("session-1")
        second_pause = await controller.request_pause("session-1")
        assert first_pause == second_pause
        first_grant = await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        second_grant = await controller.grant_human_control(
            "session-1",
            operator_id="op-1",
            display_name="Alex",
        )
        assert first_grant == second_grant

    asyncio.run(scenario())
