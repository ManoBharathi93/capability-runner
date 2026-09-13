"""Reviewer-facing composition for the three reproducible demo flows."""

from __future__ import annotations

import asyncio
import json
import threading
from collections import Counter
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast, runtime_checkable
from uuid import uuid4

import httpx
from flask import Flask
from werkzeug.serving import make_server

from capability_runner.application.demo_configuration import (
    DEMO_CAPABILITY_ID,
    DEMO_CAPABILITY_VERSION,
    build_core_bank_demo_profile,
    build_demo_automation_policy,
    build_demo_capability,
    build_demo_capability_request,
    build_demo_operator_policy,
    trusted_success_targets,
)
from capability_runner.application.operator_console import OperatorConsoleService
from capability_runner.application.run_coordinator import (
    ReplayContinuationCoordinator,
    ReplayContinuationRegistry,
    ReplayContinuationResumeValidator,
)
from capability_runner.capabilities.capability_builder import CapabilityBuilder
from capability_runner.capabilities.capability_store import CapabilityStore
from capability_runner.capabilities.capability_validator import ValidatedCapability
from capability_runner.contracts.continuation import ReplayContinuationResult
from capability_runner.contracts.discovery import DiscoveryResult
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayResult,
)
from capability_runner.contracts.intervention import InterventionRecord
from capability_runner.contracts.operator_console import OperatorControlDescriptor
from capability_runner.contracts.replay import ReplayResult
from capability_runner.contracts.requests import DiscoveryRequest
from capability_runner.contracts.surfaces import SurfaceSessionRef
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.discovery import configuration as model_configuration
from capability_runner.discovery.discovery_engine import DiscoveryEngine
from capability_runner.discovery.snapshot_collector import DiscoverySnapshotCollector
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.interfaces.async_core_runner import AsyncCoreRunner
from capability_runner.interfaces.operator_http import create_operator_console_app
from capability_runner.intervention.intervention_manager import InterventionManager
from capability_runner.intervention.operator_action_gateway import OperatorActionGateway
from capability_runner.replay.replay_engine import ReplayEngine
from capability_runner.replay.snapshot_collector import SnapshotCollector
from capability_runner.replay.state_evaluator import StateEvaluator
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter

from .app import DemoScenario, create_app

DEFAULT_OUTPUT_ROOT = Path("var/demo-runs")
DISCOVERY_MEMBER_ID = "67890"
REPLAY_MEMBER_ID = "12345"
UNKNOWN_MEMBER_ID = "00000"


class DemoRunError(RuntimeError):
    """A reviewer demo did not achieve its expected outcome."""


@runtime_checkable
class AsyncClosable(Protocol):
    async def aclose(self) -> None: ...


@dataclass(frozen=True, slots=True)
class DemoRunResult:
    run_directory: Path
    summary_path: Path
    summary: dict[str, object]


@dataclass(frozen=True, slots=True)
class _DiscoveryExecution:
    result: DiscoveryResult
    provider: str
    control_stopped: bool
    surface_closed: bool


@dataclass(frozen=True, slots=True)
class _ReplayExecution:
    result: ReplayResult
    executed_actions: Counter[str]
    control_stopped: bool
    surface_closed: bool


@dataclass(slots=True)
class _InterventionExecution:
    adapter: BrowserSurfaceAdapter
    controller: SessionController
    session: SurfaceSessionRef
    record: InterventionRecord
    console: OperatorConsoleService
    coordinator: ReplayContinuationCoordinator
    automation_counter: _ExecutedActionCounter
    operator_counter: _ExecutedOperatorActionCounter
    initial_result: ReplayResult
    manager: InterventionManager
    login_required: bool = False


class _ExecutedActionCounter:
    def __init__(self, delegate: ActionGateway) -> None:
        self._delegate = delegate
        self.executed: Counter[str] = Counter()

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        result = await self._delegate.execute(request, context)
        if result.outcome == "EXECUTED":
            self.executed[request.semantic_target.value] += 1
        return result


class _ExecutedOperatorActionCounter:
    def __init__(self, delegate: OperatorActionGateway) -> None:
        self._delegate = delegate
        self.executed: Counter[str] = Counter()

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
        *,
        operator_id: str,
    ) -> GatewayResult:
        result = await self._delegate.execute(request, context, operator_id=operator_id)
        if result.outcome == "EXECUTED":
            self.executed[request.semantic_target.value] += 1
        return result


@contextmanager
def serve_app(app: Flask, *, port: int = 0) -> Generator[str, None, None]:
    server = make_server("127.0.0.1", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def run_through_line(
    *,
    environment: Mapping[str, str],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
) -> DemoRunResult:
    config = model_configuration.load_model_provider_config(environment)
    effective_run_id = run_id or _new_run_id("through-line")
    recorder = _recorder(output_root, effective_run_id, DISCOVERY_MEMBER_ID, REPLAY_MEMBER_ID)

    with serve_app(create_app(scenario=DemoScenario(mode="normal"))) as base_url:
        with AsyncCoreRunner(timeout_seconds=240) as async_runner:
            discovery = async_runner.run(
                _run_discovery(
                    base_url=base_url,
                    run_id=effective_run_id,
                    recorder=recorder,
                    config=config,
                )
            )
            _require(discovery.result.outcome == "SUCCESS", "Discovery did not succeed.")
            _require(discovery.result.turns > 0, "Discovery made no model calls.")
            _require(
                discovery.result.verified_targets
                == tuple(target.value for target in trusted_success_targets()),
                "Discovery did not verify all required targets.",
            )

            recorder.record(
                EvidenceEvent(
                    event_type="lifecycle",
                    component="reviewer-demo",
                    run_id=effective_run_id,
                    outcome="started",
                    reason_code="CAPABILITY_BUILD_STARTED",
                    metadata={
                        "discovery_action_count": discovery.result.actions,
                        "discovery_turn_count": discovery.result.turns,
                    },
                )
            )
            built = CapabilityBuilder().build(build_demo_capability_request(discovery.result))
            recorder.record(
                EvidenceEvent(
                    event_type="outcome",
                    component="reviewer-demo",
                    run_id=effective_run_id,
                    outcome="validated",
                    reason_code="CAPABILITY_VALIDATED",
                    metadata={
                        "capability_id": built.definition.capability_id,
                        "capability_version": built.definition.capability_version,
                        "input_count": len(built.definition.inputs),
                        "step_count": len(built.definition.steps),
                    },
                )
            )
            run_directory = recorder.run_directory
            store = CapabilityStore(run_directory / "capabilities")
            artifact_path = store.save(built)
            recorder.record(
                EvidenceEvent(
                    event_type="outcome",
                    component="reviewer-demo",
                    run_id=effective_run_id,
                    outcome="stored",
                    reason_code="CAPABILITY_STORED",
                    metadata={
                        "artifact_path": artifact_path.relative_to(run_directory).as_posix(),
                        "capability_id": built.definition.capability_id,
                        "capability_version": built.definition.capability_version,
                    },
                )
            )
            loaded = store.load(DEMO_CAPABILITY_ID, DEMO_CAPABILITY_VERSION)
            _require(loaded == built, "Stored capability did not round-trip safely.")
            recorder.record(
                EvidenceEvent(
                    event_type="outcome",
                    component="reviewer-demo",
                    run_id=effective_run_id,
                    outcome="loaded",
                    reason_code="CAPABILITY_LOADED",
                    metadata={
                        "capability_id": loaded.definition.capability_id,
                        "capability_version": loaded.definition.capability_version,
                        "round_trip_verified": True,
                    },
                )
            )

            artifact_text = artifact_path.read_text(encoding="utf-8").casefold()
            artifact_checks = {
                "discovery_value_embedded": any(
                    value.casefold() in artifact_text
                    for value in (DISCOVERY_MEMBER_ID, "98765", "$987.65 usd")
                ),
                "browser_selectors_embedded": any(
                    value in artifact_text
                    for value in ("#member_id", "button[type='submit']", "#account-balance")
                ),
                "provider_identity_embedded": any(
                    value.casefold() in artifact_text for value in (config.provider, config.model)
                ),
            }
            _require(not any(artifact_checks.values()), "Generated capability leaked runtime data.")

            replay = async_runner.run(
                _run_replay(
                    base_url=base_url,
                    run_id=effective_run_id,
                    control_session_id=f"replay-{effective_run_id}",
                    recorder=recorder,
                    capability=loaded,
                    member_id=REPLAY_MEMBER_ID,
                )
            )

    _require(discovery.control_stopped, "Discovery control session did not stop.")
    _require(discovery.surface_closed, "Discovery browser session did not close.")
    _require(replay.result.outcome == "SUCCESS", "Fresh Replay did not succeed.")
    _require(
        replay.result.outputs == {"balance_minor_units": 438221, "currency": "USD"},
        "Fresh Replay returned unexpected outputs.",
    )
    _require(replay.control_stopped and replay.surface_closed, "Replay resources did not close.")

    summary: dict[str, object] = {
        "schema_version": 1,
        "run_id": effective_run_id,
        "demo_kind": "through-line",
        "status": "SUCCESS",
        "capability_id": DEMO_CAPABILITY_ID,
        "capability_version": DEMO_CAPABILITY_VERSION,
        "discovery_result": discovery.result.outcome,
        "replay_result": replay.result.outcome,
        "balance_minor_units": replay.result.outputs["balance_minor_units"],
        "currency": replay.result.outputs["currency"],
        "discovery_model_calls": discovery.result.turns,
        "builder_model_calls": 0,
        "replay_model_calls": 0,
        "browser_action_count": discovery.result.actions + sum(replay.executed_actions.values()),
        "provider": discovery.provider,
        "discovery_session_destroyed": discovery.control_stopped and discovery.surface_closed,
        "fresh_replay_session": True,
        "artifact_checks": artifact_checks,
        "evidence_file": recorder.path.relative_to(recorder.run_directory).as_posix(),
        "artifact_file": artifact_path.relative_to(recorder.run_directory).as_posix(),
    }
    return write_summary(recorder.run_directory, summary)


def run_exception(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
) -> DemoRunResult:
    effective_run_id = run_id or _new_run_id("exception")
    recorder = _recorder(output_root, effective_run_id, UNKNOWN_MEMBER_ID)
    with serve_app(create_app(scenario=DemoScenario(mode="normal"))) as base_url:
        replay = asyncio.run(
            _run_replay(
                base_url=base_url,
                run_id=effective_run_id,
                control_session_id=f"replay-{effective_run_id}",
                recorder=recorder,
                capability=build_demo_capability(),
                member_id=UNKNOWN_MEMBER_ID,
            )
        )

    _require(
        replay.result.outcome == "BUSINESS_OUTCOME",
        "Exceptional Replay was not classified as a business outcome.",
    )
    _require(
        replay.result.business_outcome_code == "MEMBER_NOT_FOUND",
        "Exceptional Replay returned the wrong business outcome.",
    )
    _require(replay.control_stopped and replay.surface_closed, "Replay resources did not close.")

    summary: dict[str, object] = {
        "schema_version": 1,
        "run_id": effective_run_id,
        "demo_kind": "exception",
        "status": "SUCCESS",
        "capability_id": DEMO_CAPABILITY_ID,
        "capability_version": DEMO_CAPABILITY_VERSION,
        "replay_result": replay.result.outcome,
        "business_outcome": replay.result.business_outcome_code,
        "discovery_model_calls": 0,
        "builder_model_calls": 0,
        "replay_model_calls": 0,
        "browser_action_count": sum(replay.executed_actions.values()),
        "evidence_file": recorder.path.relative_to(recorder.run_directory).as_posix(),
        "artifact_file": None,
    }
    return write_summary(recorder.run_directory, summary)


def run_replay(
    *,
    member_id: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
) -> DemoRunResult:
    effective_run_id = run_id or _new_run_id("replay")
    recorder = _recorder(output_root, effective_run_id, member_id)
    with serve_app(create_app(scenario=DemoScenario(mode="normal"))) as base_url:
        replay = asyncio.run(
            _run_replay(
                base_url=base_url,
                run_id=effective_run_id,
                control_session_id=f"replay-{effective_run_id}",
                recorder=recorder,
                capability=build_demo_capability(),
                member_id=member_id,
            )
        )

    _require(replay.control_stopped and replay.surface_closed, "Replay resources did not close.")
    summary: dict[str, object] = {
        "schema_version": 1,
        "run_id": effective_run_id,
        "demo_kind": "replay",
        "status": replay.result.outcome,
        "capability_id": DEMO_CAPABILITY_ID,
        "capability_version": DEMO_CAPABILITY_VERSION,
        "replay_result": replay.result.outcome,
        "business_outcome": replay.result.business_outcome_code,
        "failure_reason": replay.result.reason_code if replay.result.outcome == "FAILURE" else None,
        "outputs": replay.result.outputs,
        "discovery_model_calls": 0,
        "builder_model_calls": 0,
        "replay_model_calls": 0,
        "browser_action_count": sum(replay.executed_actions.values()),
        "evidence_file": recorder.path.relative_to(recorder.run_directory).as_posix(),
        "artifact_file": None,
    }
    return write_summary(recorder.run_directory, summary)


def run_intervention(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
) -> DemoRunResult:
    effective_run_id = run_id or _new_run_id("intervention")
    recorder = _recorder(output_root, effective_run_id, DISCOVERY_MEMBER_ID)
    with serve_app(create_app(scenario=DemoScenario(mode="normal"))) as base_url:
        with AsyncCoreRunner(timeout_seconds=60) as async_runner:
            live = async_runner.run(
                prepare_intervention(
                    base_url=base_url,
                    run_id=effective_run_id,
                    recorder=recorder,
                )
            )
            operator_app = create_operator_console_app(
                console=live.console,
                async_runner=async_runner,
            )
            try:
                with (
                    serve_app(operator_app) as operator_url,
                    httpx.Client(
                        base_url=operator_url,
                        timeout=15,
                    ) as client,
                ):
                    page = client.get(f"/operator/interventions/{live.record.intervention_id}")
                    human_click = client.post(
                        f"/api/interventions/{live.record.intervention_id}/actions",
                        json={
                            "semantic_target": "member.accounts.savings",
                            "action_kind": "click",
                        },
                    )
                    returned = client.post(
                        f"/api/interventions/{live.record.intervention_id}/return-control"
                    )
                _require(page.status_code == 200, "Operator console page was unavailable.")
                _require(
                    human_click.status_code == 200 and human_click.json().get("executed") is True,
                    "Operator Savings action did not execute.",
                )
                _require(
                    returned.status_code == 200
                    and returned.json().get("control_state") == "resume_requested",
                    "Operator did not return control for validation.",
                )
                resumed = async_runner.run(live.coordinator.resume(live.record.intervention_id))
            finally:
                async_runner.run(close_intervention(live))

    verify_intervention(live, resumed)
    replay_result = resumed.replay_result
    assert replay_result is not None
    repeated_side_effects = sum(live.automation_counter.executed.values()) != 3
    summary: dict[str, object] = {
        "schema_version": 1,
        "run_id": effective_run_id,
        "demo_kind": "intervention",
        "status": "SUCCESS",
        "capability_id": DEMO_CAPABILITY_ID,
        "capability_version": DEMO_CAPABILITY_VERSION,
        "operator_mode": "automated_http",
        "blocked_action": "member.accounts.savings",
        "same_surface_session": live.record.surface_session == live.session,
        "generation_before": resumed.generation_before,
        "generation_after": resumed.generation_after,
        "replay_result": replay_result.outcome,
        "balance_minor_units": replay_result.outputs["balance_minor_units"],
        "currency": replay_result.outputs["currency"],
        "repeated_automation_side_effects": repeated_side_effects,
        "discovery_model_calls": 0,
        "builder_model_calls": 0,
        "replay_model_calls": 0,
        "browser_action_count": (
            sum(live.automation_counter.executed.values())
            + sum(live.operator_counter.executed.values())
        ),
        "evidence_file": recorder.path.relative_to(recorder.run_directory).as_posix(),
        "artifact_file": None,
    }
    return write_summary(recorder.run_directory, summary)


async def _run_discovery(
    *,
    base_url: str,
    run_id: str,
    recorder: EvidenceRecorder,
    config: model_configuration.ModelProviderConfig,
) -> _DiscoveryExecution:
    profile = build_core_bank_demo_profile(f"{base_url}/")
    adapter = BrowserSurfaceAdapter(headless=True)
    controller = SessionController()
    model_client = model_configuration.create_model_client(config)
    session: SurfaceSessionRef | None = None
    control_opened = False
    result: DiscoveryResult | None = None
    control_stopped = False
    surface_closed = False
    try:
        session = await adapter.open_surface_session(profile)
        await controller.open_session(session_id=f"discovery-{run_id}", run_id=run_id)
        control_opened = True
        context = GatewayExecutionContext(
            run_id=run_id,
            control_session_id=f"discovery-{run_id}",
            expected_generation=0,
            surface_session=session,
            profile=profile,
        )
        gateway = ActionGateway(
            policy_guard=PolicyGuard(build_demo_automation_policy(require_savings_approval=False)),
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
        )
        result = await DiscoveryEngine(
            model_client=model_client,
            action_gateway=gateway,
            snapshot_collector=DiscoverySnapshotCollector(adapter),
            evidence_recorder=recorder,
        ).discover(
            DiscoveryRequest(
                goal="Find the savings balance for member 67890.",
                target=ProfileTarget(
                    application="corebank",
                    profile="legacy-browser",
                    entry_url=f"{base_url}/",
                ),
                max_steps=12,
                timeout_seconds=180,
                required_completion_targets=trusted_success_targets(),
            ),
            context,
        )
        if result.outcome == "FAILED":
            await _record_surface_failure(result, adapter, session, recorder)
    finally:
        if control_opened:
            stopped = await controller.stop_session(f"discovery-{run_id}")
            control_stopped = stopped.control_state == "terminal"
        if session is not None:
            await adapter.close_surface_session(session)
            surface_closed = True
        await adapter.aclose()
        if isinstance(model_client, AsyncClosable):
            await model_client.aclose()

    if result is None:
        raise DemoRunError("Discovery ended without a result.")
    return _DiscoveryExecution(
        result=result,
        provider=config.provider,
        control_stopped=control_stopped,
        surface_closed=surface_closed,
    )


async def _run_replay(
    *,
    base_url: str,
    run_id: str,
    control_session_id: str,
    recorder: EvidenceRecorder,
    capability: ValidatedCapability,
    member_id: str,
) -> _ReplayExecution:
    profile = build_core_bank_demo_profile(f"{base_url}/")
    adapter = BrowserSurfaceAdapter(headless=True)
    controller = SessionController()
    gateway = ActionGateway(
        policy_guard=PolicyGuard(build_demo_automation_policy(require_savings_approval=False)),
        session_controller=controller,
        surface_adapter=adapter,
        evidence_recorder=recorder,
    )
    counter = _ExecutedActionCounter(gateway)
    session: SurfaceSessionRef | None = None
    control_opened = False
    result: ReplayResult | None = None
    control_stopped = False
    surface_closed = False
    try:
        session = await adapter.open_surface_session(profile)
        state = await controller.open_session(session_id=control_session_id, run_id=run_id)
        control_opened = True
        result = await ReplayEngine(
            action_gateway=cast(ActionGateway, counter),
            snapshot_collector=SnapshotCollector(adapter),
            state_evaluator=StateEvaluator(),
            evidence_recorder=recorder,
        ).replay(
            capability,
            {"member_id": member_id},
            GatewayExecutionContext(
                run_id=run_id,
                control_session_id=control_session_id,
                expected_generation=state.control_generation,
                surface_session=session,
                profile=profile,
            ),
        )
        if result.outcome == "BUSINESS_OUTCOME":
            recorder.record(
                EvidenceEvent(
                    event_type="outcome",
                    component="reviewer-demo",
                    run_id=run_id,
                    session_id=control_session_id,
                    outcome="business_outcome",
                    reason_code=result.business_outcome_code or "BUSINESS_OUTCOME",
                    summary="Replay reached a known business outcome.",
                    metadata={"classification": "known_business_outcome"},
                )
            )
        elif result.outcome == "FAILURE" and result.checkpoint is None:
            await _record_surface_failure(result, adapter, session, recorder)
    finally:
        if control_opened:
            stopped = await controller.stop_session(control_session_id)
            control_stopped = stopped.control_state == "terminal"
        if session is not None:
            await adapter.close_surface_session(session)
            surface_closed = True
        await adapter.aclose()

    if result is None:
        raise DemoRunError("Replay ended without a result.")
    return _ReplayExecution(
        result=result,
        executed_actions=counter.executed,
        control_stopped=control_stopped,
        surface_closed=surface_closed,
    )


async def prepare_intervention(
    *,
    base_url: str,
    run_id: str,
    recorder: EvidenceRecorder,
    headless: bool = True,
    grant_operator: bool = True,
    login_required: bool = False,
) -> _InterventionExecution:
    profile = build_core_bank_demo_profile(f"{base_url}/")
    capability = build_demo_capability()
    policy = build_demo_automation_policy(require_savings_approval=True)
    if login_required:
        from .login_handoff import build_login_handoff

        profile, policy, capability = build_login_handoff(base_url)
    adapter = BrowserSurfaceAdapter(headless=headless)
    controller = SessionController()
    automation_gateway = ActionGateway(
        policy_guard=PolicyGuard(policy),
        session_controller=controller,
        surface_adapter=adapter,
        evidence_recorder=recorder,
    )
    automation_counter = _ExecutedActionCounter(automation_gateway)
    operator_counter = _ExecutedOperatorActionCounter(
        OperatorActionGateway(
            policy_guard=PolicyGuard(build_demo_operator_policy()),
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
        )
    )
    replay_engine = ReplayEngine(
        action_gateway=cast(ActionGateway, automation_counter),
        snapshot_collector=SnapshotCollector(adapter),
        state_evaluator=StateEvaluator(),
        evidence_recorder=recorder,
    )
    registry = ReplayContinuationRegistry()
    validator = ReplayContinuationResumeValidator(
        registry=registry,
        replay_engine=replay_engine,
    )
    manager = InterventionManager(
        session_controller=controller,
        resume_validator=validator,
        evidence_recorder=recorder,
    )
    coordinator = ReplayContinuationCoordinator(
        registry=registry,
        intervention_manager=manager,
        replay_engine=replay_engine,
        evidence_recorder=recorder,
    )

    session = await adapter.open_surface_session(profile)
    await controller.open_session(session_id=f"control-{run_id}", run_id=run_id)
    context = GatewayExecutionContext(
        run_id=run_id,
        control_session_id=f"control-{run_id}",
        expected_generation=0,
        surface_session=session,
        profile=profile,
    )
    initial_result = await replay_engine.replay(
        capability,
        {"member_id": DISCOVERY_MEMBER_ID},
        context,
    )
    _require(initial_result.reason_code == "APPROVAL_REQUIRED", "Replay did not pause.")
    suspended = await coordinator.suspend_for_intervention(
        intervention_id=f"intervention-{uuid4().hex}",
        replay_result=initial_result,
        capability=capability,
        runtime_inputs={"member_id": DISCOVERY_MEMBER_ID},
        context=context,
    )
    if suspended.intervention is None:
        await adapter.aclose()
        raise DemoRunError("Replay continuation was not created.")
    if grant_operator:
        granted = await manager.grant_operator_control(
            suspended.intervention.intervention_id,
            operator_id="reviewer",
            display_name="Reviewer demo",
        )
        if granted.outcome != "OPERATOR_CONTROLLED":
            await adapter.aclose()
            raise DemoRunError("Operator control was not granted.")
    console = OperatorConsoleService(
        intervention_manager=manager,
        operator_gateway=operator_counter,
        session_reader=controller,
        surface_inspector=adapter,
        view_provider=adapter,
    )
    console.register_intervention(
        record=suspended.intervention,
        profile=profile,
        operator_id="reviewer",
        controls=(
            OperatorControlDescriptor(
                semantic_target="member.accounts.savings",
                label="Savings",
                action_kind="click",
            ),
        ),
    )
    return _InterventionExecution(
        adapter=adapter,
        controller=controller,
        session=session,
        record=suspended.intervention,
        console=console,
        coordinator=coordinator,
        automation_counter=automation_counter,
        operator_counter=operator_counter,
        initial_result=initial_result,
        manager=manager,
        login_required=login_required,
    )


async def close_intervention(live: _InterventionExecution) -> None:
    await live.controller.stop_session(live.record.control_session_id)
    await live.adapter.close_surface_session(live.session)
    await live.adapter.aclose()


def verify_intervention(
    live: _InterventionExecution,
    resumed: ReplayContinuationResult,
    *,
    direct_browser: bool = False,
) -> None:
    _require(live.initial_result.reason_code == "APPROVAL_REQUIRED", "Replay did not block.")
    _require(live.record.surface_session == live.session, "Surface session changed.")
    _require(resumed.outcome == "SUCCESS", "Replay continuation did not succeed.")
    _require(resumed.generation_before == 0, "Unexpected suspended generation.")
    _require(resumed.generation_after == 3, "Control generation did not advance safely.")
    _require(resumed.replay_result is not None, "Replay continuation returned no result.")
    _require(
        resumed.replay_result.outputs
        == {
            "balance_minor_units": 98765,
            "currency": "USD",
        },
        "Replay continuation returned unexpected outputs.",
    )
    _require(
        live.automation_counter.executed
        == Counter(
            {
                "member.search.member_id": 1,
                "member.search.submit": 1,
                "member.results.open": 1,
                **({"member.accounts.savings": 1} if live.login_required else {}),
            }
        ),
        "Replay repeated a pre-intervention automation action.",
    )
    _require(
        live.operator_counter.executed
        == (Counter() if direct_browser else Counter({"member.accounts.savings": 1})),
        "Operator action count was unexpected.",
    )


async def _record_surface_failure(
    result: DiscoveryResult | ReplayResult,
    adapter: BrowserSurfaceAdapter,
    session: SurfaceSessionRef,
    recorder: EvidenceRecorder,
) -> None:
    failure = await adapter.capture_failure_evidence(session)
    if failure is None:
        return
    recorder.record(
        EvidenceEvent(
            event_type="error",
            component="reviewer-demo",
            run_id=recorder.run_directory.name,
            outcome="failure",
            reason_code=result.reason_code or "AUTOMATION_FAILURE",
            summary=failure.summary,
            metadata={"surface": failure.details},
        )
    )


def _recorder(output_root: Path, run_id: str, *sensitive_values: str) -> EvidenceRecorder:
    return EvidenceRecorder(
        output_root,
        run_id,
        redaction_context=RedactionContext(explicit_values=frozenset(sensitive_values)),
    )


def write_summary(run_directory: Path, summary: dict[str, object]) -> DemoRunResult:
    run_directory.mkdir(parents=True, exist_ok=True)
    summary_path = run_directory / "summary.json"
    summary_path.write_text(
        f"{json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True)}\n",
        encoding="utf-8",
    )
    return DemoRunResult(
        run_directory=run_directory,
        summary_path=summary_path,
        summary=summary,
    )


def _new_run_id(demo_kind: str) -> str:
    return f"{demo_kind}-{uuid4().hex}"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DemoRunError(message)
