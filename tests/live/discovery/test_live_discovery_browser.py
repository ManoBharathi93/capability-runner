from __future__ import annotations

import asyncio
import threading
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

import pytest
from werkzeug.serving import make_server

from capability_runner.capabilities.capability_builder import CapabilityBuilder
from capability_runner.capabilities.capability_store import CapabilityStore
from capability_runner.capabilities.capability_validator import ValidatedCapability
from capability_runner.contracts.capability_building import (
    CapabilityBuildRequest,
    InputEqualitySuccessTemplate,
    LiteralEqualitySuccessTemplate,
    VisibleSuccessTemplate,
)
from capability_runner.contracts.discovery import DiscoveryResult
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
from capability_runner.contracts.requests import DiscoveryRequest
from capability_runner.contracts.surfaces import SemanticTargetRef
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.discovery import configuration as model_configuration
from capability_runner.discovery.discovery_engine import DiscoveryEngine
from capability_runner.discovery.snapshot_collector import DiscoverySnapshotCollector
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

_TRUSTED_SUCCESS_TEMPLATES = (
    InputEqualitySuccessTemplate(
        target=SemanticTargetRef(value="member.details.identity"),
        input_action_target=SemanticTargetRef(value="member.search.member_id"),
    ),
    LiteralEqualitySuccessTemplate(
        target=SemanticTargetRef(value="member.account.type"),
        expected="Savings",
    ),
    VisibleSuccessTemplate(
        target=SemanticTargetRef(value="member.account.balance"),
    ),
)


@runtime_checkable
class AsyncClosable(Protocol):
    async def aclose(self) -> None: ...


@dataclass(frozen=True)
class LiveDiscoveryRun:
    result: DiscoveryResult
    provider: str
    model: str
    model_calls: int
    control_stopped: bool
    surface_closed: bool


@dataclass(frozen=True)
class FreshReplayRun:
    result: ReplayResult
    gateway_calls: Counter[str]
    gateway_sequence: tuple[str, ...]
    evidence_path: Path
    control_stopped: bool
    surface_closed: bool


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
def _serve_demo_app() -> Generator[str, None, None]:
    server = make_server(
        "127.0.0.1",
        0,
        create_app(scenario=DemoScenario(mode="normal", search_delay_seconds=0.12)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _local_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def _target(value: str) -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="live-discovery",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            FillPolicyRule(
                rule_id="fill-member-id",
                effect="ALLOW",
                semantic_target=_target("member.search.member_id"),
            ),
            ClickPolicyRule(
                rule_id="submit-search",
                effect="ALLOW",
                semantic_target=_target("member.search.submit"),
            ),
            ClickPolicyRule(
                rule_id="open-member",
                effect="ALLOW",
                semantic_target=_target("member.results.open"),
            ),
            ClickPolicyRule(
                rule_id="open-savings",
                effect="ALLOW",
                semantic_target=_target("member.accounts.savings"),
            ),
        ),
    )


def _build_request(result: DiscoveryResult) -> CapabilityBuildRequest:
    return CapabilityBuildRequest.model_validate(
        {
            "capability_id": "lookup_savings_balance",
            "capability_version": "1.0.0",
            "name": "Lookup savings balance",
            "description": "Find a member savings account and return its balance.",
            "discovery_result": result,
            "application_requirement": {
                "application_family": "corebank",
                "surface_kind": "browser",
            },
            "input_sensitivity": [
                {
                    "action_target": {"value": "member.search.member_id"},
                    "sensitive": True,
                }
            ],
            "success_templates": _TRUSTED_SUCCESS_TEMPLATES,
            "outputs": [
                {
                    "name": "balance_minor_units",
                    "value_type": "INTEGER",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_minor_units",
                    },
                },
                {
                    "name": "currency",
                    "value_type": "CURRENCY_CODE",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_code",
                    },
                },
            ],
            "business_outcomes": [
                {
                    "code": "MEMBER_NOT_FOUND",
                    "description": "The requested member was not found.",
                    "conditions": [
                        {
                            "kind": "target_visible",
                            "target": {"value": "member.search.not_found"},
                        }
                    ],
                }
            ],
            "step_metadata": [
                {
                    "action_kind": "click",
                    "target": {"value": "member.search.submit"},
                    "postcondition": {
                        "kind": "target_visible",
                        "target": {"value": "member.results.open"},
                    },
                    "retry_policy": {
                        "kind": "wait_and_retry",
                        "max_attempts": 3,
                        "delay_ms": 400,
                    },
                }
            ],
        }
    )


async def _run_live_case(
    *,
    base_url: str,
    member_id: str,
    expected_balance: str,
    evidence_root: Path,
    case_name: str,
    goal: str | None = None,
    required_completion_targets: tuple[SemanticTargetRef, ...] = (),
) -> LiveDiscoveryRun:
    profile = build_core_bank_demo_profile(f"{base_url}/")
    adapter = BrowserSurfaceAdapter(headless=True)
    controller = SessionController()
    recorder = EvidenceRecorder(evidence_root, run_id=f"discovery-{case_name}")
    gateway = ActionGateway(
        policy_guard=PolicyGuard(_policy()),
        session_controller=controller,
        surface_adapter=adapter,
        evidence_recorder=recorder,
    )
    config = model_configuration.load_model_provider_config(_local_environment())
    model_client = model_configuration.create_model_client(config)
    session = None
    control_opened = False
    result: DiscoveryResult | None = None
    control_stopped = False
    surface_closed = False
    try:
        session = await adapter.open_surface_session(profile)
        await controller.open_session(
            session_id=f"control-{case_name}",
            run_id=f"discovery-{case_name}",
        )
        control_opened = True
        context = GatewayExecutionContext(
            run_id=f"discovery-{case_name}",
            control_session_id=f"control-{case_name}",
            expected_generation=0,
            surface_session=session,
            profile=profile,
        )
        result = await DiscoveryEngine(
            model_client=model_client,
            action_gateway=gateway,
            snapshot_collector=DiscoverySnapshotCollector(adapter),
        ).discover(
            DiscoveryRequest(
                goal=goal or f"Find the savings account balance for member {member_id}",
                target=ProfileTarget.model_validate(
                    {
                        "kind": "profile",
                        "application": "corebank",
                        "profile": "legacy-browser",
                        "entry_url": f"{base_url}/",
                    }
                ),
                max_steps=12,
                timeout_seconds=180,
                required_completion_targets=required_completion_targets,
            ),
            context,
        )
        final_snapshot = await DiscoverySnapshotCollector(adapter).collect(
            session,
            profile,
            (
                _target("member.details.identity"),
                _target("member.account.balance"),
            ),
        )
        final_values = {
            item.target.value: item.text
            for item in final_snapshot.observed_targets
            if item.state == "VISIBLE"
        }

        print(
            f"live discovery case={case_name} provider={config.provider} model={config.model} "
            f"outcome={result.outcome} turns={result.turns} actions={result.actions} "
            f"verified_targets={','.join(result.verified_targets)}"
        )
        assert result.outcome == "SUCCESS", result.model_dump(mode="json")
        assert final_values["member.details.identity"] == member_id
        assert final_values["member.account.balance"] == expected_balance
        assert member_id.encode() not in recorder.path.read_bytes()
        assert member_id not in result.model_dump_json()
    finally:
        if control_opened:
            stopped = await controller.stop_session(f"control-{case_name}")
            control_stopped = stopped.control_state == "terminal"
        if session is not None:
            await adapter.close_surface_session(session)
            surface_closed = True
        await adapter.aclose()
        if isinstance(model_client, AsyncClosable):
            await model_client.aclose()

    assert result is not None
    return LiveDiscoveryRun(
        result=result,
        provider=config.provider,
        model=config.model,
        model_calls=result.turns,
        control_stopped=control_stopped,
        surface_closed=surface_closed,
    )


async def _run_fresh_replay(
    *,
    base_url: str,
    capability: ValidatedCapability,
    member_id: str,
    evidence_root: Path,
    case_name: str,
) -> FreshReplayRun:
    profile = build_core_bank_demo_profile(f"{base_url}/")
    adapter = BrowserSurfaceAdapter(headless=True)
    controller = SessionController()
    recorder = EvidenceRecorder(evidence_root, run_id=f"replay-{case_name}")
    gateway = ActionGateway(
        policy_guard=PolicyGuard(_policy()),
        session_controller=controller,
        surface_adapter=adapter,
        evidence_recorder=recorder,
    )
    counting_gateway = CountingGateway(gateway)
    session = None
    control_opened = False
    result: ReplayResult | None = None
    control_stopped = False
    surface_closed = False
    try:
        session = await adapter.open_surface_session(profile)
        control_state = await controller.open_session(
            session_id=f"control-replay-{case_name}",
            run_id=f"replay-{case_name}",
        )
        control_opened = True
        result = await ReplayEngine(
            action_gateway=cast(ActionGateway, counting_gateway),
            snapshot_collector=SnapshotCollector(adapter),
            state_evaluator=StateEvaluator(),
        ).replay(
            capability,
            {"member_id": member_id},
            GatewayExecutionContext(
                run_id=f"replay-{case_name}",
                control_session_id=f"control-replay-{case_name}",
                expected_generation=control_state.control_generation,
                surface_session=session,
                profile=profile,
            ),
        )
    finally:
        if control_opened:
            stopped = await controller.stop_session(f"control-replay-{case_name}")
            control_stopped = stopped.control_state == "terminal"
        if session is not None:
            await adapter.close_surface_session(session)
            surface_closed = True
        await adapter.aclose()

    assert result is not None
    return FreshReplayRun(
        result=result,
        gateway_calls=counting_gateway.calls,
        gateway_sequence=tuple(counting_gateway.sequence),
        evidence_path=recorder.path,
        control_stopped=control_stopped,
        surface_closed=surface_closed,
    )


@pytest.mark.live
@pytest.mark.parametrize(
    ("case_name", "member_id", "expected_balance"),
    (
        ("member-a", "67890", "$987.65 USD"),
        ("member-b", "12345", "$4,382.21 USD"),
    ),
)
def test_real_model_discovers_savings_balance_in_fresh_browser_session(
    tmp_path: Path,
    case_name: str,
    member_id: str,
    expected_balance: str,
) -> None:
    with _serve_demo_app() as base_url:
        asyncio.run(
            _run_live_case(
                base_url=base_url,
                member_id=member_id,
                expected_balance=expected_balance,
                evidence_root=tmp_path / "evidence",
                case_name=case_name,
            )
        )


@pytest.mark.live
def test_real_discovery_builds_validates_and_stores_capability(tmp_path: Path) -> None:
    member_id = "67890"
    expected_balance = "$987.65 USD"
    with _serve_demo_app() as base_url:
        discovery = asyncio.run(
            _run_live_case(
                base_url=base_url,
                member_id=member_id,
                expected_balance=expected_balance,
                evidence_root=tmp_path / "evidence",
                case_name="builder",
                goal=(
                    f"Verify member {member_id} has account type Savings and return the savings "
                    "account balance"
                ),
            )
        )
        request = _build_request(discovery.result)

        built = CapabilityBuilder().build(request)
        store = CapabilityStore(tmp_path / "capabilities")
        artifact_path = store.save(built)
        loaded = store.load("lookup_savings_balance", "1.0.0")
        serialized = artifact_path.read_text(encoding="utf-8")
        config = model_configuration.load_model_provider_config(_local_environment())

        assert loaded == built
        assert [step.action.target.value for step in loaded.definition.steps] == [
            "member.search.member_id",
            "member.search.submit",
            "member.results.open",
            "member.accounts.savings",
        ]
        assert [item.kind for item in loaded.definition.success_conditions] == [
            "target_text_equals",
            "target_text_equals",
            "target_visible",
        ]
        for forbidden in (
            member_id,
            "98765",
            expected_balance,
            config.provider,
            config.model,
            config.base_url or "unused-private-endpoint",
            "#member_id",
            "button[type='submit']",
            "#member-identity",
            "#account-type",
            "#account-balance",
            "observation_fingerprint",
            "gateway_outcome",
        ):
            assert forbidden not in serialized


@pytest.mark.live
def test_p3_4_generated_capability_replays_model_free_in_fresh_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discovery_member_id = "67890"
    discovery_balance = "$987.65 USD"

    with _serve_demo_app() as base_url:
        # DISCOVERY PHASE
        discovery = asyncio.run(
            _run_live_case(
                base_url=base_url,
                member_id=discovery_member_id,
                expected_balance=discovery_balance,
                evidence_root=tmp_path / "discovery-evidence",
                case_name="p3-4",
                goal="Find the savings balance for member 67890.",
                required_completion_targets=tuple(
                    template.target for template in _TRUSTED_SUCCESS_TEMPLATES
                ),
            )
        )
        assert discovery.result.outcome == "SUCCESS"
        assert discovery.model_calls > 0
        assert discovery.result.verified_targets == tuple(
            template.target.value for template in _TRUSTED_SUCCESS_TEMPLATES
        )

        # BUILD + STORE PHASE
        build_request = _build_request(discovery.result)
        built = CapabilityBuilder().build(build_request)
        store = CapabilityStore(tmp_path / "generated-capabilities")
        artifact_path = store.save(built)
        artifact_payload = artifact_path.read_text(encoding="utf-8")
        artifact = built.definition.model_dump(mode="json")
        model_config = model_configuration.load_model_provider_config(_local_environment())

        assert artifact["inputs"] == [
            {
                "name": "member_id",
                "value_type": "STRING",
                "required": True,
                "sensitive": True,
                "min_length": None,
                "max_length": None,
                "pattern": None,
            }
        ]
        assert [step["action"]["target"]["value"] for step in artifact["steps"]] == [
            "member.search.member_id",
            "member.search.submit",
            "member.results.open",
            "member.accounts.savings",
        ]
        assert artifact["steps"][0]["action"]["value"] == {
            "kind": "input",
            "name": "member_id",
        }
        assert [condition["kind"] for condition in artifact["success_conditions"]] == [
            "target_text_equals",
            "target_text_equals",
            "target_visible",
        ]
        assert [output["name"] for output in artifact["outputs"]] == [
            "balance_minor_units",
            "currency",
        ]
        assert [outcome["code"] for outcome in artifact["business_outcomes"]] == [
            "MEMBER_NOT_FOUND"
        ]
        assert artifact["steps"][1]["retry_policy"] == {
            "kind": "wait_and_retry",
            "max_attempts": 3,
            "delay_ms": 400,
        }

        forbidden_values = (
            discovery_member_id,
            "98765",
            discovery_balance,
            discovery.provider,
            discovery.model,
            model_config.base_url or "unused-private-endpoint",
            "gemma",
            "gemma4",
            "openai",
            "anthropic",
            "discoverytrace",
            "raw model response",
            "playwright",
            "xpath",
            "#member_id",
            "button[type='submit']",
            "#member-identity",
            "#account-type",
            "#account-balance",
        )
        serialized_casefolded = artifact_payload.casefold()
        for forbidden in forbidden_values:
            assert forbidden.casefold() not in serialized_casefolded

        # DESTROY DISCOVERY STATE
        assert discovery.control_stopped
        assert discovery.surface_closed
        discovery_model_calls = discovery.model_calls
        discovery_provider = discovery.provider
        discovery_model = discovery.model
        del build_request, built, discovery

        # MODEL-FREE REPLAY PHASE - different input
        for variable in (
            "LLM_PROVIDER",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMMA_API_KEY",
            "GEMMA_BASE_URL",
        ):
            monkeypatch.delenv(variable, raising=False)

        def fail_model_construction(*args: object, **kwargs: object) -> None:
            raise AssertionError("model construction is forbidden during replay")

        monkeypatch.setattr(
            model_configuration,
            "create_model_client",
            fail_model_construction,
        )
        loaded = store.load("lookup_savings_balance", "1.0.0")
        assert loaded.definition.model_dump(mode="json") == artifact

        cross_input = asyncio.run(
            _run_fresh_replay(
                base_url=base_url,
                capability=loaded,
                member_id="12345",
                evidence_root=tmp_path / "cross-input-evidence",
                case_name="cross-input",
            )
        )
        assert cross_input.result.outcome == "SUCCESS", cross_input.result
        assert cross_input.result.outputs == {
            "balance_minor_units": 438221,
            "currency": "USD",
        }
        assert cross_input.gateway_sequence == (
            "member.search.member_id",
            "member.search.submit",
            "member.results.open",
            "member.accounts.savings",
        )
        assert cross_input.control_stopped
        assert cross_input.surface_closed
        assert b"12345" not in cross_input.evidence_path.read_bytes()

        # MODEL-FREE REPLAY PHASE - original input in another fresh session
        original_input = asyncio.run(
            _run_fresh_replay(
                base_url=base_url,
                capability=loaded,
                member_id=discovery_member_id,
                evidence_root=tmp_path / "original-input-evidence",
                case_name="original-input",
            )
        )
        assert original_input.result.outcome == "SUCCESS", original_input.result
        assert original_input.result.outputs == {
            "balance_minor_units": 98765,
            "currency": "USD",
        }
        assert original_input.control_stopped
        assert original_input.surface_closed
        assert discovery_member_id.encode() not in original_input.evidence_path.read_bytes()

        # MODEL-FREE REPLAY PHASE - generated business outcome in a third fresh session
        not_found = asyncio.run(
            _run_fresh_replay(
                base_url=base_url,
                capability=loaded,
                member_id="00000",
                evidence_root=tmp_path / "not-found-evidence",
                case_name="not-found",
            )
        )
        assert not_found.result.outcome == "BUSINESS_OUTCOME", not_found.result
        assert not_found.result.business_outcome_code == "MEMBER_NOT_FOUND"
        assert not_found.gateway_calls["member.search.submit"] == 1
        assert not_found.gateway_calls["member.results.open"] == 0
        assert not_found.control_stopped
        assert not_found.surface_closed

        print(
            "P3.4 through-line "
            f"provider={discovery_provider} model={discovery_model} "
            f"discovery_model_calls={discovery_model_calls} "
            "builder_model_calls=0 replay_model_calls=0"
        )