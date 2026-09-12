from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import cast

from capability_runner.contracts.discovery import DiscoveryResult
from capability_runner.contracts.evaluation import EvaluationSnapshot, TargetObservation
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayResult,
)
from capability_runner.contracts.requests import DiscoveryRequest
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    SemanticTargetRef,
    SurfaceSessionRef,
)
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.discovery.discovery_engine import DiscoveryEngine
from capability_runner.discovery.model_client import ModelResponse
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interaction.action_gateway import ActionGateway
from tests.fakes.model_client import FakeModelClient


class ScriptedCollector:
    def __init__(self, snapshots: tuple[EvaluationSnapshot, ...]) -> None:
        self._snapshots = list(snapshots)

    async def collect(
        self,
        session: SurfaceSessionRef,
        profile: ApplicationProfile,
        targets: tuple[SemanticTargetRef, ...],
    ) -> EvaluationSnapshot:
        if len(self._snapshots) > 1:
            return self._snapshots.pop(0)
        return self._snapshots[0]


class GatewayFake:
    def __init__(self, results: tuple[GatewayResult, ...] = ()) -> None:
        self.requests: list[GatewayActionRequest] = []
        self._results = list(results)

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        self.requests.append(request)
        if self._results:
            return self._results.pop(0)
        return GatewayResult(
            outcome="EXECUTED",
            reason_code="APPLIED",
            summary="Applied.",
            action_id=request.action_id,
            semantic_target=request.semantic_target,
            surface_outcome="APPLIED",
        )


def _target(value: str) -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def _profile() -> ApplicationProfile:
    targets = (
        "member.search.member_id",
        "member.search.submit",
        "member.details.identity",
        "member.account.type",
        "member.account.balance",
    )
    return ApplicationProfile.model_validate(
        {
            "profile_id": "corebank-demo",
            "application_family": "corebank",
            "variant": "legacy-browser",
            "entry_point": "https://example.test/",
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=_target(target),
                    locator_candidates=(CssLocator(kind="css", selector=f"#{index}"),),
                    description=f"Trusted description {index}",
                )
                for index, target in enumerate(targets)
            ],
        }
    )


def _snapshot(
    *,
    identity: str | None = None,
    account_type: str | None = None,
    balance: str | None = None,
    marker: str = "Search",
) -> EvaluationSnapshot:
    return EvaluationSnapshot(
        observed_targets=(
            TargetObservation(target=_target("member.search.member_id"), state="VISIBLE"),
            TargetObservation(
                target=_target("member.search.submit"), state="VISIBLE", text=marker
            ),
            TargetObservation(
                target=_target("member.details.identity"),
                state="VISIBLE" if identity is not None else "NOT_VISIBLE",
                text=identity,
            ),
            TargetObservation(
                target=_target("member.account.type"),
                state="VISIBLE" if account_type is not None else "NOT_VISIBLE",
                text=account_type,
            ),
            TargetObservation(
                target=_target("member.account.balance"),
                state="VISIBLE" if balance is not None else "NOT_VISIBLE",
                text=balance,
            ),
        )
    )


def _response(payload: object) -> ModelResponse:
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return ModelResponse(content=content, provider="test", model="scripted")


def _gateway_result(outcome: str, reason_code: str) -> GatewayResult:
    return GatewayResult.model_validate(
        {
            "outcome": outcome,
            "reason_code": reason_code,
            "summary": "Scripted result.",
            "action_id": "scripted",
            "semantic_target": {"value": "member.search.submit"},
            "surface_outcome": "APPLIED" if outcome == "EXECUTED" else None,
        }
    )


def _run(
    responses: tuple[object, ...],
    *,
    snapshots: tuple[EvaluationSnapshot, ...] | None = None,
    gateway_results: tuple[GatewayResult, ...] = (),
    goal: str = "Find the savings balance for member 67890",
    max_steps: int = 12,
    required_completion_targets: tuple[SemanticTargetRef, ...] = (),
    evidence_recorder: EvidenceRecorder | None = None,
) -> tuple[DiscoveryResult, GatewayFake, FakeModelClient]:
    profile = _profile()
    model = FakeModelClient(tuple(_response(item) for item in responses))
    gateway = GatewayFake(gateway_results)
    engine = DiscoveryEngine(
        model_client=model,
        action_gateway=cast(ActionGateway, gateway),
        snapshot_collector=ScriptedCollector(snapshots or (_snapshot(),)),
        evidence_recorder=evidence_recorder,
    )
    request = DiscoveryRequest(
        goal=goal,
        target=ProfileTarget(
            kind="profile", application="corebank", profile="legacy-browser"
        ),
        max_steps=max_steps,
        required_completion_targets=required_completion_targets,
    )
    context = GatewayExecutionContext(
        run_id="run-discovery",
        control_session_id="control-discovery",
        expected_generation=0,
        surface_session=SurfaceSessionRef(surface_session_id="surface-discovery"),
        profile=profile,
    )
    result = asyncio.run(engine.discover(request, context))
    return result, gateway, model


def test_lifecycle_evidence_records_bounded_decision_facts_without_raw_text(
    tmp_path: Path,
) -> None:
    sentinel = "EVIDENCE_PRIVATE_VALUE_44192"
    recorder = EvidenceRecorder(
        tmp_path,
        run_id="run-discovery",
        redaction_context=RedactionContext(explicit_values=frozenset({sentinel})),
    )
    complete = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": sentinel},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }

    result, _, _ = _run(
        (complete,),
        goal=f"Find the savings balance for member {sentinel}",
        snapshots=(_snapshot(identity=sentinel, balance="$987.65 USD"),),
        evidence_recorder=recorder,
    )

    events = [
        EvidenceEvent.model_validate_json(line)
        for line in recorder.path.read_text(encoding="utf-8").splitlines()
    ]
    assert result.outcome == "SUCCESS"
    assert [event.reason_code for event in events] == [
        "DISCOVERY_STARTED",
        "DISCOVERY_OBSERVATION_COLLECTED",
        "DISCOVERY_DECISION_RECEIVED",
        "DISCOVERY_COMPLETED",
    ]
    assert events[2].metadata == {
        "action_kind": None,
        "decision_kind": "COMPLETE",
        "observation_fingerprint": result.trace[0].observation_fingerprint,
        "semantic_target": None,
        "turn": 1,
    }
    persisted = recorder.path.read_text(encoding="utf-8")
    assert sentinel not in persisted
    assert "$987.65 USD" not in persisted


def test_malformed_json_stops_after_two_invalid_responses() -> None:
    result, gateway, _ = _run(("not json", "still not json"))

    assert result.outcome == "FAILED"
    assert result.reason_code == "MODEL_INVALID_RESPONSE"
    assert result.turns == 2
    assert gateway.requests == []


def test_selector_target_is_rejected_before_gateway() -> None:
    payload = {"kind": "ACT", "action": {"kind": "click", "target": "#submit"}}
    result, gateway, _ = _run((payload, payload))

    assert result.reason_code == "MODEL_INVALID_RESPONSE"
    assert gateway.requests == []


def test_unknown_semantic_target_is_rejected_before_gateway() -> None:
    payload = {
        "kind": "ACT",
        "action": {"kind": "click", "target": "member.unknown.submit"},
    }
    result, gateway, _ = _run((payload, payload))

    assert result.reason_code == "UNKNOWN_TARGET"
    assert gateway.requests == []


def test_fill_value_must_be_an_exact_goal_substring() -> None:
    payload = {
        "kind": "ACT",
        "action": {
            "kind": "fill",
            "target": "member.search.member_id",
            "value": "12345",
        },
    }
    result, gateway, _ = _run((payload, payload))

    assert result.reason_code == "UNGROUNDED_FILL_VALUE"
    assert gateway.requests == []


def test_fabricated_completion_is_rejected() -> None:
    payload = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.balance", "observed_text": "$999.99 USD"},
        ],
    }
    result, gateway, _ = _run((payload, payload), snapshots=(_snapshot(),))

    assert result.reason_code == "COMPLETION_NOT_GROUNDED"
    assert gateway.requests == []


def test_stale_completion_is_repaired_against_latest_snapshot() -> None:
    click = {"kind": "ACT", "action": {"kind": "click", "target": "member.search.submit"}}
    stale = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.balance", "observed_text": "$100.00 USD"},
        ],
    }
    current = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.balance", "observed_text": "$200.00 USD"},
        ],
    }
    result, _, _ = _run(
        (click, stale, current),
        snapshots=(
            _snapshot(),
            _snapshot(identity="67890", balance="$200.00 USD"),
            _snapshot(identity="67890", balance="$200.00 USD"),
        ),
    )

    assert result.outcome == "SUCCESS"
    assert result.turns == 3
    assert result.trace[1].outcome == "COMPLETION_NOT_GROUNDED"


def test_repeated_action_on_unchanged_snapshot_stops_for_no_progress() -> None:
    click = {"kind": "ACT", "action": {"kind": "click", "target": "member.search.submit"}}
    result, gateway, _ = _run((click, click), snapshots=(_snapshot(),))

    assert result.reason_code == "NO_PROGRESS"
    assert result.actions == 1
    assert len(gateway.requests) == 1


def test_ninth_action_is_rejected_by_action_limit() -> None:
    click = {"kind": "ACT", "action": {"kind": "click", "target": "member.search.submit"}}
    result, gateway, _ = _run(
        tuple(click for _ in range(9)),
        snapshots=tuple(_snapshot(marker=f"Search {index}") for index in range(9)),
    )

    assert result.reason_code == "ACTION_LIMIT_REACHED"
    assert result.actions == 8
    assert len(gateway.requests) == 8


def test_gateway_denial_stops_without_retry() -> None:
    click = {"kind": "ACT", "action": {"kind": "click", "target": "member.search.submit"}}
    result, gateway, _ = _run(
        (click,), gateway_results=(_gateway_result("DENIED", "TARGET_NOT_ALLOWED"),)
    )

    assert result.outcome == "FAILED"
    assert result.reason_code == "POLICY_DENIED"
    assert len(gateway.requests) == 1


def test_gateway_approval_requirement_requests_intervention() -> None:
    click = {"kind": "ACT", "action": {"kind": "click", "target": "member.search.submit"}}
    result, gateway, _ = _run(
        (click,),
        gateway_results=(_gateway_result("APPROVAL_REQUIRED", "APPROVAL_REQUIRED"),),
    )

    assert result.outcome == "INTERVENTION_REQUIRED"
    assert result.reason_code == "APPROVAL_REQUIRED"
    assert len(gateway.requests) == 1


def test_uncertain_action_effect_stops_without_retry() -> None:
    click = {"kind": "ACT", "action": {"kind": "click", "target": "member.search.submit"}}
    result, gateway, _ = _run(
        (click,),
        gateway_results=(
            _gateway_result("FAILED", "ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED"),
        ),
    )

    assert result.outcome == "INTERVENTION_REQUIRED"
    assert result.reason_code == "ACTION_EFFECT_UNCERTAIN"
    assert len(gateway.requests) == 1


def test_trace_and_gateway_request_do_not_serialize_fill_value() -> None:
    sentinel = "MEMBER_PRIVATE_74291"
    fill = {
        "kind": "ACT",
        "action": {
            "kind": "fill",
            "target": "member.search.member_id",
            "value": sentinel,
        },
    }
    result, gateway, _ = _run(
        (fill, {"kind": "FAIL", "reason_code": "UNSUPPORTED_STATE"}),
        goal=f"Find the savings balance for member {sentinel}",
    )

    assert sentinel not in result.model_dump_json()
    assert sentinel not in gateway.requests[0].model_dump_json()
    assert result.trace[0].gateway_outcome == "EXECUTED"
    assert result.trace[0].value_source is not None
    assert result.trace[0].value_source.kind == "goal_span"
    assert result.trace[0].observation_fingerprint is not None


def test_success_retains_non_raw_completion_and_goal_span_relationship() -> None:
    member_id = "67890"
    fill = {
        "kind": "ACT",
        "action": {
            "kind": "fill",
            "target": "member.search.member_id",
            "value": member_id,
        },
    }
    complete = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": member_id},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }

    result, _, _ = _run(
        (fill, complete),
        snapshots=(
            _snapshot(),
            _snapshot(identity=member_id, balance="$987.65 USD"),
        ),
    )

    identity_evidence = result.completion_evidence[0]
    assert result.outcome == "SUCCESS"
    assert identity_evidence.target == "member.details.identity"
    assert identity_evidence.goal_span_action_target == "member.search.member_id"
    assert len(identity_evidence.text_fingerprint) == 64
    assert member_id not in result.model_dump_json()


def test_current_goal_grounded_completion_succeeds() -> None:
    complete = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }
    result, gateway, _ = _run(
        (complete,), snapshots=(_snapshot(identity="67890", balance="$987.65 USD"),)
    )

    assert result.outcome == "SUCCESS"
    assert result.verified_targets == (
        "member.details.identity",
        "member.account.balance",
    )
    assert gateway.requests == []


def test_missing_required_completion_target_is_rejected_without_gateway_action() -> None:
    incomplete = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }
    required = tuple(
        _target(value)
        for value in (
            "member.details.identity",
            "member.account.type",
            "member.account.balance",
        )
    )

    result, gateway, _ = _run(
        (incomplete, incomplete),
        snapshots=(
            _snapshot(
                identity="67890",
                account_type="Savings",
                balance="$987.65 USD",
            ),
        ),
        required_completion_targets=required,
    )

    assert result.outcome == "FAILED"
    assert result.reason_code == "COMPLETION_EVIDENCE_MISSING"
    assert result.trace[0].outcome == "COMPLETION_EVIDENCE_MISSING"
    assert gateway.requests == []


def test_missing_required_completion_target_can_be_repaired() -> None:
    incomplete = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }
    complete = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.type", "observed_text": "Savings"},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }
    required = tuple(
        _target(value)
        for value in (
            "member.details.identity",
            "member.account.type",
            "member.account.balance",
        )
    )

    result, gateway, _ = _run(
        (incomplete, complete),
        snapshots=(
            _snapshot(
                identity="67890",
                account_type="Savings",
                balance="$987.65 USD",
            ),
        ),
        required_completion_targets=required,
    )

    assert result.outcome == "SUCCESS"
    assert result.verified_targets == tuple(item.value for item in required)
    assert result.trace[0].outcome == "COMPLETION_EVIDENCE_MISSING"
    assert gateway.requests == []


def test_required_completion_evidence_must_match_latest_observation() -> None:
    mismatched = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.type", "observed_text": "Checking"},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }
    required = tuple(
        _target(value)
        for value in (
            "member.details.identity",
            "member.account.type",
            "member.account.balance",
        )
    )

    result, gateway, _ = _run(
        (mismatched, mismatched),
        snapshots=(
            _snapshot(
                identity="67890",
                account_type="Savings",
                balance="$987.65 USD",
            ),
        ),
        required_completion_targets=required,
    )

    assert result.outcome == "FAILED"
    assert result.reason_code == "COMPLETION_NOT_GROUNDED"
    assert gateway.requests == []


def test_unknown_required_completion_target_fails_before_model_or_gateway() -> None:
    result, gateway, model = _run(
        ({"kind": "FAIL", "reason_code": "SHOULD_NOT_RUN"},),
        required_completion_targets=(_target("member.unknown.value"),),
    )

    assert result.outcome == "FAILED"
    assert result.reason_code == "REQUIRED_COMPLETION_TARGET_UNKNOWN"
    assert result.turns == 0
    assert result.actions == 0
    assert model.requests == []
    assert gateway.requests == []


def test_empty_required_completion_targets_preserve_existing_success() -> None:
    complete = {
        "kind": "COMPLETE",
        "evidence": [
            {"target": "member.details.identity", "observed_text": "67890"},
            {"target": "member.account.balance", "observed_text": "$987.65 USD"},
        ],
    }

    result, gateway, _ = _run(
        (complete,),
        snapshots=(_snapshot(identity="67890", balance="$987.65 USD"),),
        required_completion_targets=(),
    )

    assert result.outcome == "SUCCESS"
    assert result.verified_targets == (
        "member.details.identity",
        "member.account.balance",
    )
    assert gateway.requests == []


def test_presented_observation_excludes_browser_selectors() -> None:
    result, _, model = _run(({"kind": "FAIL", "reason_code": "STOPPED"},))

    assert result.reason_code == "STOPPED"
    request_text = "\n".join(message.content for message in model.requests[0].messages)
    assert "#0" not in request_text
    assert "#1" not in request_text
    assert "locator_candidates" not in request_text