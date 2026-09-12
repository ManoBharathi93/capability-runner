from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from capability_runner.application.run_coordinator import (
    ReplayContinuationCoordinator,
    ReplayContinuationRegistry,
    ReplayContinuationResumeValidator,
)
from capability_runner.capabilities.capability_validator import (
    CapabilityValidator,
    ValidatedCapability,
)
from capability_runner.contracts.capabilities import CapabilityDefinition
from capability_runner.contracts.gateway import GatewayExecutionContext
from capability_runner.contracts.intervention import ResumeValidationResult
from capability_runner.contracts.replay import ReplayCheckpoint, ReplayResult
from capability_runner.contracts.sessions import SessionControllerError
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    SemanticTargetRef,
    SurfaceSessionRef,
)
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.session_controller import SessionController
from capability_runner.intervention.intervention_manager import InterventionManager

CAPABILITY_FIXTURE = Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json")
SENSITIVE_SENTINEL = "CONTINUATION_PRIVATE_MEMBER_83521"


class ReplayEngineFake:
    def __init__(self) -> None:
        self.validation = ResumeValidationResult(
            outcome="VALID",
            reason_code="CURRENT_TERMINAL_STATE_CONFIRMED",
            summary="Fresh terminal state was confirmed.",
        )
        self.result = ReplayResult(
            outcome="SUCCESS",
            run_id="run-1",
            outputs={"balance_minor_units": 98765, "currency": "USD"},
            summary="Declared success conditions were met.",
            steps_attempted=4,
        )
        self.validation_calls: list[GatewayExecutionContext] = []
        self.resume_calls: list[GatewayExecutionContext] = []
        self.resume_started = asyncio.Event()
        self.release_resume = asyncio.Event()
        self.block_resume = False
        self.repeat_approval = False

    async def validate_resume(
        self,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ResumeValidationResult:
        self.validation_calls.append(context)
        return self.validation

    async def resume(
        self,
        capability: ValidatedCapability,
        checkpoint: ReplayCheckpoint,
        runtime_inputs: Mapping[str, str],
        context: GatewayExecutionContext,
    ) -> ReplayResult:
        self.resume_calls.append(context)
        self.resume_started.set()
        if self.block_resume:
            await self.release_resume.wait()
        if self.repeat_approval:
            return ReplayResult(
                outcome="FAILURE",
                run_id=context.run_id,
                reason_code="APPROVAL_REQUIRED",
                step_id=checkpoint.blocked_step_id,
                summary="Approval is still required.",
                steps_attempted=checkpoint.blocked_step_index + 1,
                checkpoint=checkpoint.model_copy(
                    update={"suspended_generation": context.expected_generation}
                ),
            )
        return self.result


def _capability() -> ValidatedCapability:
    payload = json.loads(CAPABILITY_FIXTURE.read_text(encoding="utf-8"))
    return CapabilityValidator().validate(CapabilityDefinition.model_validate(payload))


def _profile() -> ApplicationProfile:
    return ApplicationProfile.model_validate(
        {
            "profile_id": "profile",
            "application_family": "corebank",
            "variant": "legacy-browser",
            "entry_point": "https://example.test/",
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(
                        value="member.accounts.savings"
                    ),
                    locator_candidates=(
                        CssLocator(kind="css", selector="#savings"),
                    ),
                )
            ],
        }
    )


def _context() -> GatewayExecutionContext:
    return GatewayExecutionContext(
        run_id="run-1",
        control_session_id="control-1",
        expected_generation=0,
        surface_session=SurfaceSessionRef(surface_session_id="surface-1"),
        profile=_profile(),
    )


def _approval_result() -> ReplayResult:
    return ReplayResult(
        outcome="FAILURE",
        run_id="run-1",
        reason_code="APPROVAL_REQUIRED",
        step_id="open_savings_account",
        summary="Approval required.",
        steps_attempted=4,
        checkpoint=ReplayCheckpoint(
            capability_id="lookup_savings_balance",
            capability_version="1.0.0",
            blocked_step_id="open_savings_account",
            blocked_step_index=3,
            suspended_generation=0,
        ),
    )


async def _harness(
    tmp_path: Path,
) -> tuple[
    SessionController,
    InterventionManager,
    ReplayContinuationCoordinator,
    ReplayContinuationRegistry,
    ReplayEngineFake,
    EvidenceRecorder,
]:
    controller = SessionController()
    await controller.open_session(session_id="control-1", run_id="run-1")
    recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
    registry = ReplayContinuationRegistry()
    engine = ReplayEngineFake()
    validator = ReplayContinuationResumeValidator(registry=registry, replay_engine=engine)
    manager = InterventionManager(
        session_controller=controller,
        resume_validator=validator,
        evidence_recorder=recorder,
    )
    coordinator = ReplayContinuationCoordinator(
        registry=registry,
        intervention_manager=manager,
        replay_engine=engine,
        evidence_recorder=recorder,
    )
    return controller, manager, coordinator, registry, engine, recorder


async def _request_and_return(
    manager: InterventionManager,
    coordinator: ReplayContinuationCoordinator,
) -> None:
    suspended = await coordinator.suspend_for_intervention(
        intervention_id="intervention-1",
        replay_result=_approval_result(),
        capability=_capability(),
        runtime_inputs={"member_id": SENSITIVE_SENTINEL},
        context=_context(),
    )
    assert suspended.outcome == "INTERVENTION_REQUIRED"
    granted = await manager.grant_operator_control(
        "intervention-1",
        operator_id="operator-1",
    )
    assert granted.outcome == "OPERATOR_CONTROLLED"
    returned = await manager.return_operator_control(
        "intervention-1",
        operator_id="operator-1",
    )
    assert returned.outcome == "RESUME_VALIDATION_REQUIRED"


def test_approval_suspends_same_session_with_masked_runtime_state(tmp_path: Path) -> None:
    async def scenario() -> None:
        _, _, coordinator, registry, _, recorder = await _harness(tmp_path)

        result = await coordinator.suspend_for_intervention(
            intervention_id="intervention-1",
            replay_result=_approval_result(),
            capability=_capability(),
            runtime_inputs={"member_id": SENSITIVE_SENTINEL},
            context=_context(),
        )

        assert result.outcome == "INTERVENTION_REQUIRED"
        assert result.intervention is not None
        assert result.intervention.surface_session == _context().surface_session
        assert result.intervention.reason_code == "APPROVAL_REQUIRED"
        assert result.intervention.summary == (
            "Human approval/action is required before automation can continue."
        )
        assert SENSITIVE_SENTINEL not in repr(registry.get("intervention-1"))
        assert SENSITIVE_SENTINEL not in repr(result)
        persisted = recorder.path.read_text(encoding="utf-8")
        assert SENSITIVE_SENTINEL not in persisted
        events = [json.loads(line) for line in persisted.splitlines()]
        context_event = next(
            event
            for event in events
            if event["reason_code"] == "INTERVENTION_CONTEXT_RECORDED"
        )
        assert context_event["step_id"] == "open_savings_account"
        assert context_event["metadata"] == {
            "action_effect_state": "NOT_EXECUTED",
            "action_kind": "click",
            "blocked_step_index": 3,
            "capability_id": "lookup_savings_balance",
            "capability_name": "Lookup savings balance",
            "capability_version": "1.0.0",
            "control_generation": 1,
            "current_state": "blocked_before_dispatch",
            "input_names": ["member_id"],
            "intervention_id": "intervention-1",
            "semantic_target": "member.accounts.savings",
            "surface_session_id": "surface-1",
        }

    asyncio.run(scenario())


def test_uncertain_effect_cannot_create_continuation(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller, _, coordinator, registry, _, _ = await _harness(tmp_path)
        uncertain = ReplayResult(
            outcome="FAILURE",
            run_id="run-1",
            reason_code="ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED",
            step_id="open_savings_account",
            summary="Effect may have occurred.",
            steps_attempted=4,
        )

        result = await coordinator.suspend_for_intervention(
            intervention_id="intervention-1",
            replay_result=uncertain,
            capability=_capability(),
            runtime_inputs={"member_id": SENSITIVE_SENTINEL},
            context=_context(),
        )

        assert result.outcome == "INVALID_CONTINUATION"
        assert registry.get("intervention-1") is None
        assert (await controller.get_session("control-1")).control_state == (
            "automation_controlled"
        )

    asyncio.run(scenario())


def test_resume_validates_fresh_state_and_uses_new_generation(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller, manager, coordinator, _, engine, _ = await _harness(tmp_path)
        await _request_and_return(manager, coordinator)

        result = await coordinator.resume("intervention-1")

        assert result.outcome == "SUCCESS"
        assert result.generation_before == 0
        assert result.generation_after == 3
        assert len(engine.validation_calls) == 1
        assert len(engine.resume_calls) == 1
        assert engine.validation_calls[0].surface_session == _context().surface_session
        assert engine.resume_calls[0].surface_session == _context().surface_session
        assert engine.resume_calls[0].expected_generation == 3
        with pytest.raises(SessionControllerError) as exc_info:
            async with controller.automation_dispatch("control-1", expected_generation=0):
                pass
        assert exc_info.value.code == "STALE_GENERATION"

    asyncio.run(scenario())


def test_operator_return_without_valid_state_does_not_resume(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller, manager, coordinator, _, engine, _ = await _harness(tmp_path)
        engine.validation = ResumeValidationResult(
            outcome="INVALID",
            reason_code="RESUME_STATE_UNVERIFIED",
            summary="Fresh state does not prove the blocked step completed.",
        )
        await _request_and_return(manager, coordinator)

        result = await coordinator.resume("intervention-1")

        assert result.outcome == "VALIDATION_FAILED"
        assert engine.resume_calls == []
        assert (await controller.get_session("control-1")).control_state == "resume_requested"

    asyncio.run(scenario())


def test_stopped_intervention_cannot_resume(tmp_path: Path) -> None:
    async def scenario() -> None:
        _, manager, coordinator, _, engine, _ = await _harness(tmp_path)
        await coordinator.suspend_for_intervention(
            intervention_id="intervention-1",
            replay_result=_approval_result(),
            capability=_capability(),
            runtime_inputs={"member_id": "67890"},
            context=_context(),
        )
        await manager.grant_operator_control("intervention-1", operator_id="operator-1")
        await manager.stop_intervention("intervention-1")

        result = await coordinator.resume("intervention-1")

        assert result.outcome == "SESSION_STOPPED"
        assert engine.resume_calls == []
        assert (await coordinator.resume("intervention-1")).outcome == (
            "CONTINUATION_ALREADY_CONSUMED"
        )

    asyncio.run(scenario())


def test_repeated_approval_creates_one_new_intervention_without_looping(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        controller, manager, coordinator, _, engine, _ = await _harness(tmp_path)
        engine.repeat_approval = True
        await _request_and_return(manager, coordinator)

        result = await coordinator.resume("intervention-1")

        assert result.outcome == "INTERVENTION_REQUIRED"
        assert result.intervention is not None
        assert result.intervention.intervention_id != "intervention-1"
        assert result.intervention.surface_session == _context().surface_session
        assert len(engine.resume_calls) == 1
        assert (await controller.get_session("control-1")).control_state == "pause_requested"

    asyncio.run(scenario())


def test_concurrent_resume_consumes_continuation_exactly_once(tmp_path: Path) -> None:
    async def scenario() -> None:
        _, manager, coordinator, _, engine, _ = await _harness(tmp_path)
        engine.block_resume = True
        await _request_and_return(manager, coordinator)

        first_task = asyncio.create_task(coordinator.resume("intervention-1"))
        await engine.resume_started.wait()
        second_started = asyncio.Event()

        async def second_resume():
            second_started.set()
            return await coordinator.resume("intervention-1")

        second_task = asyncio.create_task(second_resume())
        await second_started.wait()
        engine.release_resume.set()
        first, second = await asyncio.gather(first_task, second_task)

        assert first.outcome == "SUCCESS"
        assert second.outcome == "CONTINUATION_ALREADY_CONSUMED"
        assert len(engine.validation_calls) == 1
        assert len(engine.resume_calls) == 1

    asyncio.run(scenario())