"""In-memory control-state management for live sessions.

The controller owns session lifecycle, control ownership, generation-based
stale-work rejection, and the protected automated dispatch region. It does
not execute browser actions or record evidence.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass

from capability_runner.contracts.sessions import (
    AutomationOwner,
    OperatorOwner,
    SessionControlErrorCode,
    SessionControllerError,
    SessionState,
)

AUTOMATION_STATE = "automation_controlled"
PAUSING_STATE = "pause_requested"
HUMAN_CONTROL_STATE = "operator_controlled"
RESUME_CHECK_STATE = "resume_requested"
STOPPED_STATE = "terminal"


@dataclass(slots=True)
class _SessionRecord:
    state: SessionState
    automation_run_id: str
    state_lock: asyncio.Lock
    dispatch_lock: asyncio.Lock


class SessionController:
    def __init__(self) -> None:
        self._sessions: dict[str, _SessionRecord] = {}

    async def open_session(self, *, session_id: str, run_id: str) -> SessionState:
        if session_id in self._sessions:
            raise SessionControllerError(
                "INVALID_STATE_TRANSITION",
                session_id,
                "Session already exists.",
            )

        state = SessionState(
            session_id=session_id,
            control_state=AUTOMATION_STATE,
            owner=AutomationOwner(kind="automation", run_id=run_id),
            control_generation=0,
        )
        self._sessions[session_id] = _SessionRecord(
            state=state,
            automation_run_id=run_id,
            state_lock=asyncio.Lock(),
            dispatch_lock=asyncio.Lock(),
        )
        return state

    async def get_session(self, session_id: str) -> SessionState:
        record = self._get_record(session_id)
        return record.state

    async def request_pause(self, session_id: str) -> SessionState:
        record = self._get_record(session_id)
        async with record.state_lock:
            self._ensure_not_stopped(record.state)
            if record.state.control_state == PAUSING_STATE:
                return record.state
            if record.state.control_state != AUTOMATION_STATE:
                raise self._invalid_transition(
                    session_id,
                    "Pause can only be requested from automation.",
                )
            record.state = record.state.model_copy(
                update={
                    "control_state": PAUSING_STATE,
                    "control_generation": record.state.control_generation + 1,
                }
            )
            return record.state

    async def grant_human_control(
        self,
        session_id: str,
        *,
        operator_id: str,
        display_name: str | None = None,
    ) -> SessionState:
        record = self._get_record(session_id)
        async with record.state_lock:
            self._ensure_not_stopped(record.state)
            if record.dispatch_lock.locked():
                raise self._error(
                    "ACTION_IN_FLIGHT",
                    session_id,
                    "Automated dispatch is still in flight.",
                )
            if record.state.control_state == HUMAN_CONTROL_STATE:
                owner = record.state.owner
                if isinstance(owner, OperatorOwner) and owner.operator_id == operator_id:
                    return record.state
                raise self._invalid_transition(
                    session_id,
                    "Human control is already owned by another operator.",
                )
            if record.state.control_state != PAUSING_STATE:
                raise self._invalid_transition(
                    session_id,
                    "Human control can only be granted from pause.",
                )
            record.state = record.state.model_copy(
                update={
                    "control_state": HUMAN_CONTROL_STATE,
                    "owner": OperatorOwner(
                        kind="operator",
                        operator_id=operator_id,
                        display_name=display_name,
                    ),
                    "control_generation": record.state.control_generation + 1,
                }
            )
            return record.state

    async def return_control_for_resume_check(self, session_id: str) -> SessionState:
        record = self._get_record(session_id)
        async with record.state_lock:
            self._ensure_not_stopped(record.state)
            if record.dispatch_lock.locked():
                raise self._error(
                    "ACTION_IN_FLIGHT",
                    session_id,
                    "Operator dispatch is still in flight.",
                )
            if record.state.control_state == RESUME_CHECK_STATE:
                return record.state
            if record.state.control_state != HUMAN_CONTROL_STATE:
                raise self._invalid_transition(
                    session_id,
                    "Resume check can only follow human control.",
                )
            record.state = record.state.model_copy(update={"control_state": RESUME_CHECK_STATE})
            return record.state

    async def resume_automation_after_validation(self, session_id: str) -> SessionState:
        record = self._get_record(session_id)
        async with record.state_lock:
            self._ensure_not_stopped(record.state)
            if record.state.control_state == AUTOMATION_STATE:
                owner = record.state.owner
                if isinstance(owner, AutomationOwner):
                    return record.state
                raise self._invalid_transition(
                    session_id,
                    "Automation owner is inconsistent.",
                )
            if record.state.control_state != RESUME_CHECK_STATE:
                raise self._invalid_transition(
                    session_id,
                    "Automation can only resume after validation.",
                )
            owner = record.state.owner
            if not isinstance(owner, OperatorOwner):
                raise self._invalid_transition(
                    session_id,
                    "Resume check lost operator ownership.",
                )
            record.state = record.state.model_copy(
                update={
                    "control_state": AUTOMATION_STATE,
                    "owner": AutomationOwner(
                        kind="automation",
                        run_id=record.automation_run_id,
                    ),
                    "control_generation": record.state.control_generation + 1,
                }
            )
            return record.state

    async def stop_session(self, session_id: str) -> SessionState:
        record = self._get_record(session_id)
        async with record.state_lock:
            if record.state.control_state == STOPPED_STATE:
                return record.state
            record.state = record.state.model_copy(
                update={
                    "control_state": STOPPED_STATE,
                    "control_generation": record.state.control_generation + 1,
                }
            )
            return record.state

    @asynccontextmanager
    async def automation_dispatch(self, session_id: str, expected_generation: int):
        record = self._get_record(session_id)
        async with record.dispatch_lock:
            async with record.state_lock:
                self._ensure_not_stopped(record.state)
                if record.state.control_generation != expected_generation:
                    raise self._error(
                        "STALE_GENERATION",
                        session_id,
                        "Control generation is stale.",
                    )
                if record.state.control_state != AUTOMATION_STATE:
                    raise self._error(
                        "DISPATCH_NOT_ALLOWED",
                        session_id,
                        "Automated dispatch is not allowed in the current control state.",
                    )
                if not isinstance(record.state.owner, AutomationOwner):
                    raise self._error(
                        "NOT_AUTOMATION_OWNER",
                        session_id,
                        "Session is not automation-owned.",
                    )

            try:
                yield record.state
            finally:
                pass

    @asynccontextmanager
    async def operator_dispatch(
        self,
        session_id: str,
        expected_generation: int,
        operator_id: str,
    ):
        record = self._get_record(session_id)
        async with record.dispatch_lock:
            async with record.state_lock:
                self._ensure_not_stopped(record.state)
                if record.state.control_generation != expected_generation:
                    raise self._error(
                        "STALE_GENERATION",
                        session_id,
                        "Control generation is stale.",
                    )
                if record.state.control_state != HUMAN_CONTROL_STATE:
                    raise self._error(
                        "DISPATCH_NOT_ALLOWED",
                        session_id,
                        "Operator dispatch is not allowed in the current control state.",
                    )
                owner = record.state.owner
                if not isinstance(owner, OperatorOwner) or owner.operator_id != operator_id:
                    raise self._error(
                        "NOT_OPERATOR_OWNER",
                        session_id,
                        "Session is not owned by this operator.",
                    )

            try:
                yield record.state
            finally:
                pass

    def _get_record(self, session_id: str) -> _SessionRecord:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise self._error("SESSION_NOT_FOUND", session_id, "Session does not exist.") from exc

    @staticmethod
    def _ensure_not_stopped(state: SessionState) -> None:
        if state.control_state == STOPPED_STATE:
            raise SessionControllerError("SESSION_STOPPED", state.session_id, "Session is stopped.")

    @staticmethod
    def _error(
        code: SessionControlErrorCode,
        session_id: str | None,
        summary: str,
    ) -> SessionControllerError:
        return SessionControllerError(code, session_id, summary)

    def _invalid_transition(self, session_id: str, summary: str) -> SessionControllerError:
        return self._error("INVALID_STATE_TRANSITION", session_id, summary)
