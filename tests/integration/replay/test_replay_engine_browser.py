from __future__ import annotations

import asyncio
import json
import threading
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import pytest
from werkzeug.serving import make_server

from capability_runner.capabilities.capability_validator import (
    CapabilityValidator,
    ValidatedCapability,
)
from capability_runner.contracts.capabilities import CapabilityDefinition
from capability_runner.contracts.gateway import (
    GatewayActionRequest,
    GatewayExecutionContext,
    GatewayResult,
)
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.replay import ReplayResult
from capability_runner.contracts.surfaces import SemanticTargetRef
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.replay.replay_engine import ReplayEngine
from capability_runner.replay.snapshot_collector import SnapshotCollector
from capability_runner.replay.state_evaluator import StateEvaluator
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter
from demo_app.app import DemoScenario, create_app
from tests.fixtures.corebank_browser_profile import build_core_bank_demo_profile


class CountingGateway:
    def __init__(self, gateway: ActionGateway) -> None:
        self._gateway = gateway
        self.calls: Counter[str] = Counter()
        self.sequence: list[str] = []

    async def execute(
        self,
        request: GatewayActionRequest,
        context: GatewayExecutionContext,
    ) -> GatewayResult:
        self.calls[request.semantic_target.value] += 1
        self.sequence.append(request.semantic_target.value)
        return await self._gateway.execute(request, context)


@contextmanager
def _serve(scenario: DemoScenario) -> Generator[str, None, None]:
    server = make_server("127.0.0.1", 0, create_app(scenario=scenario))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def _capability() -> ValidatedCapability:
    payload = json.loads(
        Path("tests/fixtures/capabilities/lookup_savings_balance.v1.json").read_text(
            encoding="utf-8"
        )
    )
    return CapabilityValidator().validate(CapabilityDefinition.model_validate(payload))


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="replay",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            FillPolicyRule(
                rule_id="fill",
                effect="ALLOW",
                semantic_target=SemanticTargetRef(value="member.search.member_id"),
            ),
            ClickPolicyRule(
                rule_id="search",
                effect="ALLOW",
                semantic_target=SemanticTargetRef(value="member.search.submit"),
            ),
            ClickPolicyRule(
                rule_id="open-member",
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


def _run_replay(
    tmp_path: Path,
    scenario: DemoScenario,
    member_id: str,
) -> tuple[ReplayResult, CountingGateway, EvidenceRecorder]:
    with _serve(scenario) as base_url:
        async def execute() -> tuple[ReplayResult, CountingGateway, EvidenceRecorder]:
            profile = build_core_bank_demo_profile(f"{base_url}/")
            adapter = BrowserSurfaceAdapter(headless=True)
            controller = SessionController()
            evidence_recorder = EvidenceRecorder(tmp_path / "evidence", run_id="replay")
            gateway = ActionGateway(
                policy_guard=PolicyGuard(_policy()),
                session_controller=controller,
                surface_adapter=adapter,
                evidence_recorder=evidence_recorder,
            )
            counting_gateway = CountingGateway(gateway)
            try:
                session = await adapter.open_surface_session(profile)
                await controller.open_session(session_id="control", run_id="replay")
                result = await ReplayEngine(
                    action_gateway=cast(ActionGateway, counting_gateway),
                    snapshot_collector=SnapshotCollector(adapter),
                    state_evaluator=StateEvaluator(),
                ).replay(
                    _capability(),
                    {"member_id": member_id},
                    GatewayExecutionContext(
                        run_id="replay",
                        control_session_id="control",
                        expected_generation=0,
                        surface_session=session,
                        profile=profile,
                    ),
                )
                return result, counting_gateway, evidence_recorder
            finally:
                await adapter.aclose()

        return asyncio.run(execute())


@pytest.mark.parametrize(
    ("member_id", "balance"),
    [("12345", 438221), ("67890", 98765)],
)
def test_real_browser_replay_returns_parameterized_success(
    tmp_path: Path,
    member_id: str,
    balance: int,
) -> None:
    result, gateway, _ = _run_replay(
        tmp_path,
        DemoScenario(mode="normal", search_delay_seconds=0.02),
        member_id,
    )

    assert result.outcome == "SUCCESS", result
    assert result.outputs == {"balance_minor_units": balance, "currency": "USD"}
    assert gateway.calls["member.search.submit"] == 1
    assert gateway.sequence == [
        "member.search.member_id",
        "member.search.submit",
        "member.results.open",
        "member.accounts.savings",
    ]


def test_real_browser_replay_returns_declared_member_not_found(tmp_path: Path) -> None:
    result, gateway, _ = _run_replay(
        tmp_path,
        DemoScenario(mode="normal", search_delay_seconds=0.02),
        "00000",
    )

    assert result.outcome == "BUSINESS_OUTCOME"
    assert result.business_outcome_code == "MEMBER_NOT_FOUND"
    assert gateway.calls["member.search.submit"] == 1
    assert gateway.calls["member.results.open"] == 0


def test_real_browser_replay_restricted_member_is_not_not_found(tmp_path: Path) -> None:
    result, gateway, _ = _run_replay(
        tmp_path,
        DemoScenario(mode="normal", search_delay_seconds=0.02),
        "55555",
    )

    assert result.outcome != "SUCCESS"
    assert result.business_outcome_code != "MEMBER_NOT_FOUND"
    assert gateway.calls["member.search.submit"] == 1


def test_real_browser_replay_session_expired_is_non_success(tmp_path: Path) -> None:
    result, gateway, _ = _run_replay(
        tmp_path,
        DemoScenario(mode="session_expired"),
        "12345",
    )

    assert result.outcome != "SUCCESS"
    assert result.business_outcome_code != "MEMBER_NOT_FOUND"
    assert gateway.calls["member.search.member_id"] == 1
    assert gateway.calls["member.search.submit"] == 0


def test_real_browser_replay_succeeds_without_model_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMMA_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(variable, raising=False)

    result, _, evidence_recorder = _run_replay(
        tmp_path,
        DemoScenario(mode="normal", search_delay_seconds=0.02),
        "67890",
    )

    assert result.outcome == "SUCCESS"
    assert result.outputs == {"balance_minor_units": 98765, "currency": "USD"}
    assert b"67890" not in evidence_recorder.path.read_bytes()


def test_real_browser_replay_slow_search_within_observation_bound(tmp_path: Path) -> None:
    result, gateway, _ = _run_replay(
        tmp_path,
        DemoScenario(mode="slow_search", search_delay_seconds=0.2),
        "67890",
    )

    assert result.outcome == "SUCCESS", result
    assert result.outputs == {"balance_minor_units": 98765, "currency": "USD"}
    assert gateway.calls["member.search.submit"] == 1
    assert gateway.calls["member.results.open"] == 1


def test_real_browser_replay_slow_search_beyond_observation_bound(tmp_path: Path) -> None:
    result, gateway, _ = _run_replay(
        tmp_path,
        DemoScenario(mode="slow_search", search_delay_seconds=5.0),
        "67890",
    )

    assert result.outcome == "FAILURE", result
    assert result.reason_code == "STEP_TIMEOUT", result
    assert gateway.calls["member.search.submit"] == 1
    assert gateway.calls["member.results.open"] == 0
