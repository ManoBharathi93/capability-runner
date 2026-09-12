from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import HttpUrl

from capability_runner.capabilities.capability_validator import (
    CapabilityValidator,
    ValidatedCapability,
)
from capability_runner.contracts.actions import ActionSpec
from capability_runner.contracts.capabilities import CapabilityDefinition, FillActionTemplate
from capability_runner.contracts.evaluation import EvaluationSnapshot, TargetObservation
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayOutcome,
    GatewayResult,
)
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.replay import ReplayCheckpoint, ReplayResult
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    InputValueRef,
    SemanticTargetRef,
    SurfaceActionResult,
    SurfaceSessionRef,
)
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.replay.replay_engine import ReplayEngine
from capability_runner.replay.snapshot_collector import SnapshotCollector
from capability_runner.replay.state_evaluator import StateEvaluator
from capability_runner.surfaces.surface_adapter import SurfaceAdapter

CAPABILITY_FIXTURE = Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json")
SENSITIVE_SENTINEL = "MEMBER_REPLAY_PRIVATE_57193"
REQUIRED_TARGETS = (
    "member.search.member_id",
    "member.search.submit",
    "member.results.open",
    "member.details.identity",
    "member.account.type",
    "member.accounts.savings",
    "member.account.balance",
    "member.search.not_found",
)


class GatewayPlanFake:
    def __init__(self, responses: list[GatewayResult] | None = None) -> None:
        self.requests: list[GatewayActionRequest] = []
        self._responses = list(responses or [])

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return GatewayResult(
            outcome="EXECUTED",
            reason_code="APPLIED",
            summary="Applied.",
            action_id=request.action_id,
            semantic_target=request.semantic_target,
            surface_outcome="APPLIED",
        )


class ScriptedCollector:
    def __init__(self, snapshots: list[EvaluationSnapshot]) -> None:
        self.calls = 0
        self._snapshots = list(snapshots)

    async def collect(
        self,
        session: SurfaceSessionRef,
        profile: ApplicationProfile,
        targets: tuple[SemanticTargetRef, ...],
    ) -> EvaluationSnapshot:
        self.calls += 1
        if not self._snapshots:
            return _empty_snapshot()
        if len(self._snapshots) > 1:
            return self._snapshots.pop(0)
        return self._snapshots[0]


class AppliedSurfaceAdapter:
    async def perform_action(
        self,
        session: SurfaceSessionRef,
        action: ActionSpec,
        binding: BrowserTargetBinding,
    ) -> SurfaceActionResult:
        return SurfaceActionResult(
            outcome="APPLIED",
            summary="Applied.",
            action=action,
            resolved_target=binding.semantic_target,
        )


def _capability() -> ValidatedCapability:
    payload = json.loads(CAPABILITY_FIXTURE.read_text(encoding="utf-8"))
    return CapabilityValidator().validate(CapabilityDefinition.model_validate(payload))


def _optional_input_capability() -> ValidatedCapability:
    definition = CapabilityDefinition.model_validate(
        {
            "schema_version": 1,
            "capability_id": "optional_input_wait",
            "capability_version": "1.0.0",
            "name": "Optional input wait",
            "description": "Waits on an optional precondition input.",
            "application_requirement": {
                "application_family": "corebank",
                "surface_kind": "browser",
            },
            "inputs": [
                {
                    "name": "search_hint",
                    "value_type": "STRING",
                    "required": False,
                }
            ],
            "outputs": [],
            "steps": [
                {
                    "kind": "action",
                    "step_id": "submit_search",
                    "action": {
                        "kind": "click",
                        "target": {"value": "member.search.submit"},
                    },
                    "precondition": {
                        "kind": "target_text_equals",
                        "target": {"value": "member.search.member_id"},
                        "expected": {"kind": "input", "name": "search_hint"},
                    },
                }
            ],
            "success_conditions": [
                {
                    "kind": "target_visible",
                    "target": {"value": "member.search.submit"},
                }
            ],
            "business_outcomes": [],
        }
    )
    return CapabilityValidator().validate(definition)


def _context(profile: ApplicationProfile) -> GatewayExecutionContext:
    return GatewayExecutionContext(
        run_id="run-1",
        control_session_id="control-1",
        expected_generation=0,
        surface_session=SurfaceSessionRef(surface_session_id="surface-1"),
        profile=profile,
    )


def _profile(*targets: str, application_family: str = "corebank") -> ApplicationProfile:
    target_bindings = tuple(
        BrowserTargetBinding(
            semantic_target=SemanticTargetRef(value=target),
            locator_candidates=(CssLocator(kind="css", selector="#x"),),
        )
        for target in targets
    )
    return ApplicationProfile(
        profile_id="profile",
        application_family=application_family,
        variant="test",
        entry_point=HttpUrl("http://127.0.0.1/"),
        target_bindings=target_bindings,
    )


def _empty_snapshot() -> EvaluationSnapshot:
    return EvaluationSnapshot(observed_targets=())


def _visible(target: str, text: str) -> TargetObservation:
    return TargetObservation(target=SemanticTargetRef(value=target), state="VISIBLE", text=text)


def _unavailable(target: str) -> TargetObservation:
    return TargetObservation(target=SemanticTargetRef(value=target), state="UNAVAILABLE")


def _not_visible(target: str) -> TargetObservation:
    return TargetObservation(target=SemanticTargetRef(value=target), state="NOT_VISIBLE")


def _snapshot(*observations: TargetObservation) -> EvaluationSnapshot:
    return EvaluationSnapshot(observed_targets=tuple(observations))


def _money_text(balance_minor_units: int, currency: str = "USD") -> str:
    whole_units, fractional_units = divmod(balance_minor_units, 100)
    return f"${whole_units:,}.{fractional_units:02d} {currency}"


def _success_sequence(member_id: str, balance_minor_units: int) -> list[EvaluationSnapshot]:
    return [
        _empty_snapshot(),
        _empty_snapshot(),
        _empty_snapshot(),
        _empty_snapshot(),
        _empty_snapshot(),
        _snapshot(
            _visible("member.results.open", "Open"),
            _not_visible("member.search.not_found"),
        ),
        _snapshot(
            _visible("member.details.identity", member_id),
            _visible("member.account.type", "Savings"),
            _not_visible("member.account.balance"),
            _not_visible("member.search.not_found"),
        ),
        _snapshot(
            _visible("member.details.identity", member_id),
            _visible("member.account.type", "Savings"),
            _not_visible("member.account.balance"),
            _not_visible("member.search.not_found"),
        ),
        _snapshot(
            _visible("member.details.identity", member_id),
            _visible("member.account.type", "Savings"),
            _visible("member.account.balance", _money_text(balance_minor_units)),
            _not_visible("member.search.not_found"),
        ),
        _snapshot(
            _visible("member.details.identity", member_id),
            _visible("member.account.type", "Savings"),
            _visible("member.account.balance", _money_text(balance_minor_units)),
            _not_visible("member.search.not_found"),
        ),
    ]


def _not_found_sequence() -> list[EvaluationSnapshot]:
    return [
        _empty_snapshot(),
        _empty_snapshot(),
        _empty_snapshot(),
        _snapshot(
            _visible("member.search.not_found", "No member found for the supplied Member ID.")
        ),
    ]


def _replay(
    gateway: object,
    collector: object,
    *,
    profile: ApplicationProfile | None = None,
    capability: ValidatedCapability | None = None,
    runtime_inputs: dict[str, str] | None = None,
    evidence_recorder: EvidenceRecorder | None = None,
) -> ReplayResult:
    engine = ReplayEngine(
        action_gateway=cast(ActionGateway, gateway),
        snapshot_collector=cast(SnapshotCollector, collector),
        state_evaluator=StateEvaluator(),
        evidence_recorder=evidence_recorder,
    )
    actual_profile = profile or _profile(*REQUIRED_TARGETS)
    return asyncio.run(
        engine.replay(
            capability or _capability(),
            runtime_inputs if runtime_inputs is not None else {"member_id": "12345"},
            _context(actual_profile),
        )
    )


def test_lifecycle_evidence_records_blocked_step_without_runtime_input(
    tmp_path: Path,
) -> None:
    recorder = EvidenceRecorder(
        tmp_path,
        run_id="run-1",
        redaction_context=RedactionContext(
            explicit_values=frozenset({"EVIDENCE_PRIVATE_VALUE_44192"})
        ),
    )
    gateway = GatewayPlanFake(
        [_gateway_result("APPROVAL_REQUIRED", "APPROVAL_REQUIRED", "Approval required.")]
    )

    result = _replay(
        gateway,
        ScriptedCollector([_empty_snapshot()]),
        runtime_inputs={"member_id": "EVIDENCE_PRIVATE_VALUE_44192"},
        evidence_recorder=recorder,
    )

    events = [
        EvidenceEvent.model_validate_json(line)
        for line in recorder.path.read_text(encoding="utf-8").splitlines()
    ]
    assert result.reason_code == "APPROVAL_REQUIRED"
    assert [event.reason_code for event in events] == [
        "REPLAY_STARTED",
        "REPLAY_STEP_STARTED",
        "REPLAY_STEP_BLOCKED",
        "REPLAY_COMPLETED",
    ]
    assert events[2].step_id == "enter_member_id"
    assert events[2].metadata["action_effect_state"] == "NOT_EXECUTED"
    persisted = recorder.path.read_text(encoding="utf-8")
    assert "EVIDENCE_PRIVATE_VALUE_44192" not in persisted


def _gateway_result(outcome: GatewayOutcome, reason_code: str, summary: str) -> GatewayResult:
    return GatewayResult(
        outcome=outcome,
        reason_code=reason_code,
        summary=summary,
        action_id="seed",
        semantic_target=SemanticTargetRef(value="member.search.submit"),
    )


def test_missing_required_input_prevents_gateway_actions() -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector([_empty_snapshot()])

    result = _replay(gateway, collector, capability=capability, runtime_inputs={})

    assert result.reason_code == "RUNTIME_INPUT_MISSING"
    assert gateway.requests == []


def test_wrong_application_family_prevents_gateway_actions() -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector([_empty_snapshot()])

    result = _replay(
        gateway,
        collector,
        capability=capability,
        profile=_profile(
            "member.search.member_id", "member.search.submit", application_family="not-corebank"
        ),
    )

    assert result.reason_code == "PROFILE_INCOMPATIBLE"
    assert gateway.requests == []


def test_missing_required_binding_prevents_gateway_actions() -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector([_empty_snapshot()])

    result = _replay(
        gateway,
        collector,
        capability=capability,
        profile=_profile(
            "member.search.member_id",
            "member.search.submit",
            "member.results.open",
            "member.accounts.savings",
        ),
    )

    assert result.reason_code == "TARGET_BINDING_MISSING"
    assert gateway.requests == []


def test_member_not_found_stops_before_open_step() -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector(_not_found_sequence())

    result = _replay(
        gateway, collector, capability=capability, runtime_inputs={"member_id": "00000"}
    )

    assert result.outcome == "BUSINESS_OUTCOME"
    assert result.business_outcome_code == "MEMBER_NOT_FOUND"
    assert [request.step_id for request in gateway.requests] == [
        "enter_member_id",
        "submit_member_search",
    ]


def test_retry_observation_reaches_success_without_replaying_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector(_success_sequence("67890", 98765))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMMA_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    result = _replay(
        gateway, collector, capability=capability, runtime_inputs={"member_id": "67890"}
    )

    assert result.outcome == "SUCCESS", result
    assert result.outputs == {"balance_minor_units": 98765, "currency": "USD"}
    assert [request.step_id for request in gateway.requests].count("submit_member_search") == 1
    assert collector.calls == 10


def test_retry_observation_times_out_without_replaying_search() -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector(
        [
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
        ]
    )

    result = _replay(
        gateway, collector, capability=capability, runtime_inputs={"member_id": "12345"}
    )

    assert result.reason_code == "STEP_TIMEOUT"
    assert [request.step_id for request in gateway.requests].count("submit_member_search") == 1
    assert collector.calls == 6


def test_false_success_replay_does_not_override_wrong_member_terminal_state() -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector(
        [
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _snapshot(
                _visible("member.results.open", "Open"), _not_visible("member.search.not_found")
            ),
            _snapshot(
                _visible("member.details.identity", "67890"),
                _visible("member.account.type", "Savings"),
                _not_visible("member.account.balance"),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.details.identity", "67890"),
                _visible("member.account.type", "Savings"),
                _not_visible("member.account.balance"),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.details.identity", "67890"),
                _visible("member.account.type", "Savings"),
                _visible("member.account.balance", _money_text(98765)),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.details.identity", "67890"),
                _visible("member.account.type", "Savings"),
                _visible("member.account.balance", _money_text(98765)),
                _not_visible("member.search.not_found"),
            ),
        ]
    )

    result = _replay(
        gateway, collector, capability=capability, runtime_inputs={"member_id": "12345"}
    )

    assert result.outcome != "SUCCESS"
    assert result.reason_code == "INCOMPLETE"


@pytest.mark.parametrize(
    ("gateway_result", "expected_reason"),
    [
        (_gateway_result("DENIED", "POLICY_DENIED", "Denied."), "POLICY_DENIED"),
        (
            _gateway_result("APPROVAL_REQUIRED", "APPROVAL_REQUIRED", "Approval required."),
            "APPROVAL_REQUIRED",
        ),
        (_gateway_result("FAILED", "STALE_GENERATION", "Stale generation."), "STALE_GENERATION"),
        (
            _gateway_result("FAILED", "NOT_AUTOMATION_OWNER", "Not automation owner."),
            "NOT_AUTOMATION_OWNER",
        ),
        (_gateway_result("FAILED", "SESSION_STOPPED", "Session stopped."), "SESSION_STOPPED"),
        (_gateway_result("FAILED", "TARGET_NOT_FOUND", "Target not found."), "TARGET_NOT_FOUND"),
        (_gateway_result("FAILED", "TARGET_AMBIGUOUS", "Target ambiguous."), "TARGET_AMBIGUOUS"),
        (_gateway_result("FAILED", "SURFACE_TIMEOUT", "Surface timeout."), "SURFACE_TIMEOUT"),
        (
            _gateway_result(
                "FAILED", "ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED", "Effect may have occurred."
            ),
            "ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED",
        ),
    ],
)
def test_gateway_result_mappings_stop_replay(
    gateway_result: GatewayResult,
    expected_reason: str,
) -> None:
    capability = _capability()
    gateway = GatewayPlanFake([gateway_result])
    collector = ScriptedCollector([_empty_snapshot()])

    result = _replay(gateway, collector, capability=capability)

    assert result.outcome == "FAILURE"
    assert result.reason_code == expected_reason
    assert len(gateway.requests) == 1


def test_only_approval_required_produces_a_resumable_checkpoint() -> None:
    capability = _capability()
    approval_gateway = GatewayPlanFake(
        [_gateway_result("APPROVAL_REQUIRED", "APPROVAL_REQUIRED", "Approval required.")]
    )
    uncertain_gateway = GatewayPlanFake(
        [
            _gateway_result(
                "FAILED",
                "ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED",
                "Effect may have occurred.",
            )
        ]
    )

    approval = _replay(approval_gateway, ScriptedCollector([_empty_snapshot()]))
    uncertain = _replay(uncertain_gateway, ScriptedCollector([_empty_snapshot()]))

    checkpoint = approval.checkpoint
    assert checkpoint is not None
    assert checkpoint == ReplayCheckpoint(
        capability_id=capability.definition.capability_id,
        capability_version=capability.definition.capability_version,
        blocked_step_id="enter_member_id",
        blocked_step_index=0,
        suspended_generation=0,
    )
    assert checkpoint.action_effect_state == "NOT_EXECUTED"
    assert uncertain.checkpoint is None
    assert SENSITIVE_SENTINEL not in repr(approval.checkpoint)


def test_resume_fresh_terminal_success_extracts_outputs_without_dispatch() -> None:
    capability = _capability()
    profile = _profile(*REQUIRED_TARGETS)
    gateway = GatewayPlanFake()
    engine = ReplayEngine(
        action_gateway=cast(ActionGateway, gateway),
        snapshot_collector=cast(
            SnapshotCollector,
            ScriptedCollector([_success_sequence("67890", 98765)[-1]]),
        ),
        state_evaluator=StateEvaluator(),
    )

    result = asyncio.run(
        engine.resume(
            capability,
            ReplayCheckpoint(
                capability_id=capability.definition.capability_id,
                capability_version=capability.definition.capability_version,
                blocked_step_id="open_savings_account",
                blocked_step_index=3,
                suspended_generation=0,
            ),
            {"member_id": "67890"},
            _context(profile).model_copy(update={"expected_generation": 3}),
        )
    )

    assert result.outcome == "SUCCESS"
    assert result.outputs == {"balance_minor_units": 98765, "currency": "USD"}
    assert gateway.requests == []


def test_resume_uses_fresh_postcondition_to_skip_human_completed_step() -> None:
    capability = _capability()
    profile = _profile(*REQUIRED_TARGETS)
    gateway = GatewayPlanFake()
    collector = ScriptedCollector(
        [
            _snapshot(
                _visible("member.results.open", "Open"),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.results.open", "Open"),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.details.identity", "67890"),
                _visible("member.account.type", "Savings"),
                _visible("member.account.balance", _money_text(98765)),
                _not_visible("member.search.not_found"),
            ),
        ]
    )
    engine = ReplayEngine(
        action_gateway=cast(ActionGateway, gateway),
        snapshot_collector=cast(SnapshotCollector, collector),
        state_evaluator=StateEvaluator(),
    )

    result = asyncio.run(
        engine.resume(
            capability,
            ReplayCheckpoint(
                capability_id=capability.definition.capability_id,
                capability_version=capability.definition.capability_version,
                blocked_step_id="submit_member_search",
                blocked_step_index=1,
                suspended_generation=0,
            ),
            {"member_id": "67890"},
            _context(profile).model_copy(update={"expected_generation": 3}),
        )
    )

    assert result.outcome == "SUCCESS"
    assert [request.step_id for request in gateway.requests] == ["open_matching_member"]


def test_resume_rejects_stale_generation_before_observation_or_dispatch(
    tmp_path: Path,
) -> None:
    capability = _capability()
    profile = _profile(*REQUIRED_TARGETS)
    gateway = GatewayPlanFake()
    collector = ScriptedCollector([_empty_snapshot()])
    recorder = EvidenceRecorder(tmp_path, run_id="run-1")
    engine = ReplayEngine(
        action_gateway=cast(ActionGateway, gateway),
        snapshot_collector=cast(SnapshotCollector, collector),
        state_evaluator=StateEvaluator(),
        evidence_recorder=recorder,
    )

    result = asyncio.run(
        engine.resume(
            capability,
            ReplayCheckpoint(
                capability_id=capability.definition.capability_id,
                capability_version=capability.definition.capability_version,
                blocked_step_id="enter_member_id",
                blocked_step_index=0,
                suspended_generation=0,
            ),
            {"member_id": "67890"},
            _context(profile),
        )
    )

    assert result.reason_code == "STALE_GENERATION"
    assert collector.calls == 0
    assert gateway.requests == []
    events = [
        EvidenceEvent.model_validate_json(line)
        for line in recorder.path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event.reason_code for event in events] == [
        "REPLAY_RESUME_STARTED",
        "REPLAY_COMPLETED",
    ]
    assert events[0].metadata["blocked_step_id"] == "enter_member_id"
    assert events[0].metadata["checkpoint_generation"] == 0


def test_resume_without_terminal_or_postcondition_proof_does_not_dispatch() -> None:
    capability = _capability()
    profile = _profile(*REQUIRED_TARGETS)
    gateway = GatewayPlanFake()
    collector = ScriptedCollector(
        [
            _snapshot(
                _visible("member.details.identity", "67890"),
                _visible("member.account.type", "Savings"),
                _not_visible("member.account.balance"),
                _not_visible("member.search.not_found"),
            )
        ]
    )
    engine = ReplayEngine(
        action_gateway=cast(ActionGateway, gateway),
        snapshot_collector=cast(SnapshotCollector, collector),
        state_evaluator=StateEvaluator(),
    )

    result = asyncio.run(
        engine.resume(
            capability,
            ReplayCheckpoint(
                capability_id=capability.definition.capability_id,
                capability_version=capability.definition.capability_version,
                blocked_step_id="open_savings_account",
                blocked_step_index=3,
                suspended_generation=0,
            ),
            {"member_id": "67890"},
            _context(profile).model_copy(update={"expected_generation": 3}),
        )
    )

    assert result.reason_code == "RESUME_STATE_UNVERIFIED"
    assert gateway.requests == []


def test_resume_rechecks_policy_once_when_postcondition_proves_step_pending() -> None:
    capability = _capability()
    profile = _profile(*REQUIRED_TARGETS)
    gateway = GatewayPlanFake(
        [_gateway_result("APPROVAL_REQUIRED", "APPROVAL_REQUIRED", "Approval required.")]
    )
    pending = _snapshot(
        _not_visible("member.results.open"),
        _not_visible("member.search.not_found"),
    )
    collector = ScriptedCollector([pending, pending])
    engine = ReplayEngine(
        action_gateway=cast(ActionGateway, gateway),
        snapshot_collector=cast(SnapshotCollector, collector),
        state_evaluator=StateEvaluator(),
    )

    result = asyncio.run(
        engine.resume(
            capability,
            ReplayCheckpoint(
                capability_id=capability.definition.capability_id,
                capability_version=capability.definition.capability_version,
                blocked_step_id="submit_member_search",
                blocked_step_index=1,
                suspended_generation=0,
            ),
            {"member_id": "67890"},
            _context(profile).model_copy(update={"expected_generation": 3}),
        )
    )

    assert result.reason_code == "APPROVAL_REQUIRED"
    assert result.checkpoint is not None
    assert result.checkpoint.suspended_generation == 3
    assert [request.step_id for request in gateway.requests] == ["submit_member_search"]


def test_optional_input_unknown_is_reported_as_invalid_input() -> None:
    capability = _optional_input_capability()
    profile = _profile("member.search.member_id", "member.search.submit")
    gateway = GatewayPlanFake()
    collector = ScriptedCollector([_snapshot(_visible("member.search.member_id", "12345"))])

    result = _replay(gateway, collector, capability=capability, profile=profile, runtime_inputs={})

    assert result.reason_code == "INVALID_INPUT"
    assert gateway.requests == []


def test_restricted_and_session_expired_states_are_non_success() -> None:
    capability = _capability()

    restricted_gateway = GatewayPlanFake()
    restricted_collector = ScriptedCollector(
        [
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _empty_snapshot(),
            _snapshot(
                _visible("member.results.open", "Open"), _not_visible("member.search.not_found")
            ),
            _snapshot(
                _visible("member.details.identity", "55555"),
                _visible("member.account.type", "Savings"),
                _not_visible("member.account.balance"),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.details.identity", "55555"),
                _visible("member.account.type", "Savings"),
                _not_visible("member.account.balance"),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.details.identity", "55555"),
                _visible("member.account.type", "Savings"),
                _unavailable("member.account.balance"),
                _not_visible("member.search.not_found"),
            ),
            _snapshot(
                _visible("member.details.identity", "55555"),
                _visible("member.account.type", "Savings"),
                _unavailable("member.account.balance"),
                _not_visible("member.search.not_found"),
            ),
        ]
    )
    session_expired_gateway = GatewayPlanFake()
    session_expired_collector = ScriptedCollector(
        [
            _snapshot(
                _unavailable("member.search.member_id"), _unavailable("member.search.submit")
            ),
            _snapshot(
                _unavailable("member.search.member_id"), _unavailable("member.search.submit")
            ),
            _snapshot(
                _unavailable("member.search.member_id"), _unavailable("member.search.submit")
            ),
            _snapshot(
                _unavailable("member.search.member_id"), _unavailable("member.search.submit")
            ),
            _snapshot(
                _unavailable("member.search.member_id"), _unavailable("member.search.submit")
            ),
            _snapshot(
                _unavailable("member.search.member_id"), _unavailable("member.search.submit")
            ),
        ]
    )

    restricted_result = _replay(
        restricted_gateway,
        restricted_collector,
        capability=capability,
        runtime_inputs={"member_id": "55555"},
    )
    session_expired_result = _replay(
        session_expired_gateway,
        session_expired_collector,
        capability=capability,
        runtime_inputs={"member_id": "12345"},
    )

    assert restricted_result.outcome != "SUCCESS"
    assert restricted_result.reason_code == "INCOMPLETE"
    assert session_expired_result.outcome != "SUCCESS"
    assert session_expired_result.reason_code == "STEP_TIMEOUT"


def test_replay_redacts_sensitive_input_in_gateway_evidence(tmp_path: Path) -> None:
    capability = _capability()
    profile = _profile(*REQUIRED_TARGETS)
    evidence_recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
    controller = SessionController()
    asyncio.run(controller.open_session(session_id="control-1", run_id="run-1"))
    gateway = ActionGateway(
        policy_guard=PolicyGuard(
            PolicyDefinition(
                policy_id="replay",
                version="1",
                allowed_contexts=(
                    TrustedApplicationProfile(application="corebank", profile="test"),
                ),
                rules=(
                    FillPolicyRule(
                        rule_id="fill",
                        effect="ALLOW",
                        semantic_target=SemanticTargetRef(value="member.search.member_id"),
                    ),
                    ClickPolicyRule(
                        rule_id="submit",
                        effect="ALLOW",
                        semantic_target=SemanticTargetRef(value="member.search.submit"),
                    ),
                    ClickPolicyRule(
                        rule_id="open-result",
                        effect="ALLOW",
                        semantic_target=SemanticTargetRef(value="member.results.open"),
                    ),
                    ClickPolicyRule(
                        rule_id="open-savings",
                        effect="ALLOW",
                        semantic_target=SemanticTargetRef(value="member.accounts.savings"),
                    ),
                ),
            )
        ),
        session_controller=controller,
        surface_adapter=cast(SurfaceAdapter, AppliedSurfaceAdapter()),
        evidence_recorder=evidence_recorder,
    )
    collector = ScriptedCollector(_success_sequence(SENSITIVE_SENTINEL, 438221))

    result = _replay(
        gateway,
        collector,
        capability=capability,
        profile=profile,
        runtime_inputs={"member_id": SENSITIVE_SENTINEL},
    )

    evidence_bytes = evidence_recorder.path.read_bytes()
    assert result.outcome == "SUCCESS", result
    assert SENSITIVE_SENTINEL.encode("utf-8") not in evidence_bytes


def test_replay_succeeds_without_model_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capability = _capability()
    gateway = GatewayPlanFake()
    collector = ScriptedCollector(_success_sequence("67890", 98765))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMMA_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    result = _replay(
        gateway, collector, capability=capability, runtime_inputs={"member_id": "67890"}
    )

    assert result.outcome == "SUCCESS"
    assert result.outputs == {"balance_minor_units": 98765, "currency": "USD"}


def test_replay_does_not_mutate_capability_profile_or_inputs() -> None:
    capability = _capability()
    profile = _profile(*REQUIRED_TARGETS)
    runtime_inputs = {"member_id": "12345"}
    capability_before = capability.definition.model_dump(mode="json")
    profile_before = profile.model_dump(mode="json")
    inputs_before = dict(runtime_inputs)

    result = _replay(
        GatewayPlanFake(),
        ScriptedCollector(_success_sequence("12345", 438221)),
        capability=capability,
        profile=profile,
        runtime_inputs=runtime_inputs,
    )

    assert result.outcome == "SUCCESS"
    assert capability.definition.model_dump(mode="json") == capability_before
    assert profile.model_dump(mode="json") == profile_before
    assert runtime_inputs == inputs_before
    assert isinstance(capability.definition.steps[0].action, FillActionTemplate)
    assert isinstance(capability.definition.steps[0].action.value, InputValueRef)
    assert capability.definition.steps[0].action.value.name == "member_id"
