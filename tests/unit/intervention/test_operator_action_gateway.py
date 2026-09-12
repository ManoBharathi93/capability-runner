from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import SecretStr

from capability_runner.contracts.actions import ActionSpec, ClickAction, FillAction
from capability_runner.contracts.gateway import GatewayActionRequest, GatewayExecutionContext
from capability_runner.contracts.observations import ObservationSpec
from capability_runner.contracts.policy import (
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    SemanticTargetRef,
    SurfaceActionResult,
    SurfaceFailureEvidence,
    SurfaceSessionRef,
    TargetInspectionResult,
)
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.intervention.operator_action_gateway import OperatorActionGateway


class RecordingSurfaceAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[SurfaceSessionRef, ActionSpec, BrowserTargetBinding]] = []

    async def open_surface_session(self, profile: ApplicationProfile) -> SurfaceSessionRef:
        raise AssertionError("not used")

    async def observe_surface(self, session: SurfaceSessionRef) -> ObservationSpec:
        raise AssertionError("not used")

    async def perform_action(
        self,
        session: SurfaceSessionRef,
        action: ActionSpec,
        binding: BrowserTargetBinding,
    ) -> SurfaceActionResult:
        self.calls.append((session, action, binding))
        return SurfaceActionResult(
            outcome="APPLIED",
            summary="Applied.",
            action=action,
            resolved_target=binding.semantic_target,
        )

    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult:
        raise AssertionError("not used")

    async def capture_failure_evidence(
        self,
        session: SurfaceSessionRef,
    ) -> SurfaceFailureEvidence | None:
        raise AssertionError("not used")

    async def close_surface_session(self, session: SurfaceSessionRef) -> None:
        raise AssertionError("not used")


def _target(value: str = "member.search.member_id") -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def _profile() -> ApplicationProfile:
    return ApplicationProfile.model_validate(
        {
            "profile_id": "profile",
            "application_family": "corebank",
            "variant": "legacy-browser",
            "entry_point": "https://example.test/",
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=_target(),
                    locator_candidates=(CssLocator(kind="css", selector="#member-id"),),
                )
            ],
        }
    )


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="operator-policy",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            FillPolicyRule(
                rule_id="operator-fill-member-id",
                effect="ALLOW",
                semantic_target=_target(),
            ),
        ),
    )


def _request(value: str = "12345") -> GatewayActionRequest:
    return GatewayActionRequest(
        action_id="operator-action-1",
        semantic_target=_target(),
        action=FillAction.model_construct(target=None, value=SecretStr(value)),
        step_id="manual-fill",
    )


def _context(generation: int) -> GatewayExecutionContext:
    return GatewayExecutionContext(
        run_id="run-1",
        control_session_id="control-1",
        expected_generation=generation,
        surface_session=SurfaceSessionRef(surface_session_id="surface-1"),
        profile=_profile(),
    )


async def _gateways(
    tmp_path: Path,
) -> tuple[SessionController, RecordingSurfaceAdapter, ActionGateway, OperatorActionGateway]:
    controller = SessionController()
    await controller.open_session(session_id="control-1", run_id="run-1")
    adapter = RecordingSurfaceAdapter()
    recorder = EvidenceRecorder(tmp_path / "evidence", run_id="run-1")
    policy = PolicyGuard(_policy())
    return (
        controller,
        adapter,
        ActionGateway(
            policy_guard=policy,
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
        ),
        OperatorActionGateway(
            policy_guard=policy,
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
        ),
    )


def test_operator_action_is_rejected_while_automation_owns(tmp_path: Path) -> None:
    async def scenario() -> None:
        _, adapter, _, operator_gateway = await _gateways(tmp_path)

        result = await operator_gateway.execute(
            _request(),
            _context(0),
            operator_id="operator-1",
        )

        assert result.reason_code == "DISPATCH_NOT_ALLOWED"
        assert adapter.calls == []

    asyncio.run(scenario())


def test_operator_action_succeeds_and_automation_is_rejected_during_human_control(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        controller, adapter, automation_gateway, operator_gateway = await _gateways(tmp_path)
        await controller.request_pause("control-1")
        state = await controller.grant_human_control(
            "control-1",
            operator_id="operator-1",
        )

        operator_result = await operator_gateway.execute(
            _request("67890"),
            _context(state.control_generation),
            operator_id="operator-1",
        )
        automation_result = await automation_gateway.execute(
            _request("12345").model_copy(update={"action_id": "automation-action"}),
            _context(state.control_generation),
        )

        assert operator_result.outcome == "EXECUTED"
        assert automation_result.reason_code == "DISPATCH_NOT_ALLOWED"
        assert len(adapter.calls) == 1
        assert adapter.calls[0][0] == _context(state.control_generation).surface_session

    asyncio.run(scenario())


def test_operator_action_requires_matching_operator_and_generation(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller, adapter, _, operator_gateway = await _gateways(tmp_path)
        await controller.request_pause("control-1")
        state = await controller.grant_human_control(
            "control-1",
            operator_id="operator-1",
        )

        wrong_operator = await operator_gateway.execute(
            _request(),
            _context(state.control_generation),
            operator_id="operator-2",
        )
        stale = await operator_gateway.execute(
            _request(),
            _context(0),
            operator_id="operator-1",
        )

        assert wrong_operator.reason_code == "NOT_OPERATOR_OWNER"
        assert stale.reason_code == "STALE_GENERATION"
        assert adapter.calls == []

    asyncio.run(scenario())


def test_both_action_paths_are_blocked_during_resume_validation(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller, adapter, automation_gateway, operator_gateway = await _gateways(tmp_path)
        await controller.request_pause("control-1")
        state = await controller.grant_human_control(
            "control-1",
            operator_id="operator-1",
        )
        await controller.return_control_for_resume_check("control-1")

        operator_result = await operator_gateway.execute(
            _request(),
            _context(state.control_generation),
            operator_id="operator-1",
        )
        automation_result = await automation_gateway.execute(
            _request().model_copy(update={"action_id": "automation-action"}),
            _context(state.control_generation),
        )

        assert operator_result.reason_code == "DISPATCH_NOT_ALLOWED"
        assert automation_result.reason_code == "DISPATCH_NOT_ALLOWED"
        assert adapter.calls == []

    asyncio.run(scenario())


def test_operator_fill_value_is_redacted_from_result_repr_and_evidence(tmp_path: Path) -> None:
    async def scenario() -> None:
        sentinel = "OPERATOR_PRIVATE_VALUE_61937"
        controller, adapter, _, operator_gateway = await _gateways(tmp_path)
        await controller.request_pause("control-1")
        state = await controller.grant_human_control(
            "control-1",
            operator_id="operator-1",
        )

        request = _request(sentinel)
        result = await operator_gateway.execute(
            request,
            _context(state.control_generation),
            operator_id="operator-1",
        )

        assert result.outcome == "EXECUTED"
        assert sentinel not in repr(request)
        assert sentinel not in repr(result)
        evidence_path = tmp_path / "evidence" / "run-1" / "evidence.jsonl"
        assert sentinel.encode() not in evidence_path.read_bytes()
        assert len(adapter.calls) == 1

    asyncio.run(scenario())


def test_operator_policy_and_binding_fail_closed_before_surface(tmp_path: Path) -> None:
    async def scenario() -> None:
        controller, adapter, _, operator_gateway = await _gateways(tmp_path)
        await controller.request_pause("control-1")
        state = await controller.grant_human_control(
            "control-1",
            operator_id="operator-1",
        )
        click = GatewayActionRequest(
            action_id="operator-click",
            semantic_target=_target(),
            action=ClickAction.model_construct(target=None),
        )
        missing = _request().model_copy(
            update={"semantic_target": _target("member.unknown.target")}
        )

        denied = await operator_gateway.execute(
            click,
            _context(state.control_generation),
            operator_id="operator-1",
        )
        unbound = await operator_gateway.execute(
            missing,
            _context(state.control_generation),
            operator_id="operator-1",
        )

        assert denied.outcome == "DENIED"
        assert unbound.reason_code == "TARGET_BINDING_NOT_FOUND"
        assert adapter.calls == []

    asyncio.run(scenario())