from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import SecretStr

from capability_runner.contracts.actions import ActionSpec, ClickAction, FillAction
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import GatewayActionRequest, GatewayExecutionContext
from capability_runner.contracts.observations import ObservationSpec
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.sessions import SessionControllerError
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    SemanticTargetRef,
    SurfaceActionOutcome,
    SurfaceActionResult,
    SurfaceFailureEvidence,
    SurfaceSessionRef,
    TargetInspectionResult,
)
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.interaction.action_gateway import ActionGateway, EvidenceWriter
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController


class RecordingSurfaceAdapter:
    def __init__(
        self,
        *,
        outcome: SurfaceActionOutcome = "APPLIED",
        block: asyncio.Event | None = None,
    ) -> None:
        self.outcome: SurfaceActionOutcome = outcome
        self.block = block
        self.calls: list[str] = []
        self.entered = asyncio.Event()

    async def open_surface_session(self, profile: ApplicationProfile) -> SurfaceSessionRef:
        raise AssertionError("not used by ActionGateway")

    async def observe_surface(self, session: SurfaceSessionRef) -> ObservationSpec:
        raise AssertionError("not used by ActionGateway")

    async def perform_action(
        self,
        session: SurfaceSessionRef,
        action: ActionSpec,
        binding: BrowserTargetBinding,
    ) -> SurfaceActionResult:
        self.calls.append(binding.semantic_target.value)
        self.entered.set()
        if self.block is not None:
            await self.block.wait()
        return SurfaceActionResult(
            outcome=self.outcome,
            summary=f"{self.outcome} for {binding.semantic_target.value}",
            action=action,
            resolved_target=binding.semantic_target,
        )

    async def capture_failure_evidence(
        self, session: SurfaceSessionRef
    ) -> SurfaceFailureEvidence | None:
        raise AssertionError("not used by ActionGateway")

    async def inspect_target(
        self,
        session: SurfaceSessionRef,
        binding: BrowserTargetBinding,
    ) -> TargetInspectionResult:
        return TargetInspectionResult(
            outcome="UNAVAILABLE",
            target=binding.semantic_target,
            summary="not used by ActionGateway",
        )

    async def close_surface_session(self, session: SurfaceSessionRef) -> None:
        raise AssertionError("not used by ActionGateway")


class FailingEvidenceRecorder:
    def record(self, event: EvidenceEvent, **kwargs: object) -> object:
        raise OSError("evidence unavailable")


class PostDispatchFailingEvidenceRecorder:
    def __init__(self) -> None:
        self.calls = 0

    def record(self, event: EvidenceEvent, **kwargs: object) -> object:
        self.calls += 1
        if self.calls > 1:
            raise OSError("evidence unavailable")
        return object()


def _target(value: str) -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def _profile() -> ApplicationProfile:
    return ApplicationProfile.model_validate(
        {
            "profile_id": "corebank-demo",
            "application_family": "corebank",
            "variant": "legacy-browser",
            "entry_point": "http://127.0.0.1:5000/",
            "target_bindings": (
                BrowserTargetBinding(
                    semantic_target=_target("member.search.member_id"),
                    locator_candidates=(CssLocator(kind="css", selector="#member-id"),),
                ),
                BrowserTargetBinding(
                    semantic_target=_target("member.search.submit"),
                    locator_candidates=(CssLocator(kind="css", selector="#submit"),),
                ),
            ),
        }
    )


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="gateway-policy",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            ClickPolicyRule(
                rule_id="allow-search",
                effect="ALLOW",
                semantic_target=_target("member.search.submit"),
            ),
            FillPolicyRule(
                rule_id="allow-member-id",
                effect="ALLOW",
                semantic_target=_target("member.search.member_id"),
            ),
        ),
    )


async def _context(
    controller: SessionController, *, generation: int = 0
) -> GatewayExecutionContext:
    await controller.open_session(session_id="control-1", run_id="run-1")
    return GatewayExecutionContext(
        run_id="run-1",
        control_session_id="control-1",
        expected_generation=generation,
        surface_session=SurfaceSessionRef(surface_session_id="surface-1"),
        profile=_profile(),
    )


def _gateway(
    adapter: RecordingSurfaceAdapter,
    recorder: EvidenceWriter,
) -> tuple[ActionGateway, SessionController]:
    controller = SessionController()
    return (
        ActionGateway(
            policy_guard=PolicyGuard(_policy()),
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=recorder,
        ),
        controller,
    )


def _recorder(tmp_path: Path) -> EvidenceRecorder:
    return EvidenceRecorder(tmp_path / "evidence", run_id="run-1")


def test_denied_action_never_reaches_surface_adapter(tmp_path: Path) -> None:
    async def scenario() -> None:
        adapter = RecordingSurfaceAdapter()
        gateway, controller = _gateway(adapter, _recorder(tmp_path))
        context = await _context(controller)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.search.member_id"),
            action=ClickAction.model_construct(target=None),
        )

        result = await gateway.execute(request, context)

        assert result.outcome == "DENIED"
        assert result.reason_code == "TARGET_NOT_ALLOWED"
        assert adapter.calls == []

    asyncio.run(scenario())


def test_missing_trusted_binding_never_reaches_surface_adapter(tmp_path: Path) -> None:
    async def scenario() -> None:
        adapter = RecordingSurfaceAdapter()
        gateway, controller = _gateway(adapter, _recorder(tmp_path))
        context = await _context(controller)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.unknown.control"),
            action=ClickAction.model_construct(target=None),
        )

        result = await gateway.execute(request, context)

        assert result.outcome == "FAILED"
        assert result.reason_code == "TARGET_BINDING_NOT_FOUND"
        assert adapter.calls == []

    asyncio.run(scenario())


def test_stale_or_human_owned_session_never_reaches_surface_adapter(tmp_path: Path) -> None:
    async def scenario() -> None:
        adapter = RecordingSurfaceAdapter()
        gateway, controller = _gateway(adapter, _recorder(tmp_path))
        context = await _context(controller, generation=1)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.search.submit"),
            action=ClickAction.model_construct(target=None),
        )

        stale_result = await gateway.execute(request, context)
        assert stale_result.reason_code == "STALE_GENERATION"
        await controller.request_pause("control-1")
        human_result = await gateway.execute(
            request, context.model_copy(update={"expected_generation": 1})
        )

        assert human_result.reason_code == "DISPATCH_NOT_ALLOWED"
        assert adapter.calls == []

    asyncio.run(scenario())


def test_gateway_serializes_surface_actions_per_control_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        release = asyncio.Event()
        adapter = RecordingSurfaceAdapter(block=release)
        gateway, controller = _gateway(adapter, _recorder(tmp_path))
        context = await _context(controller)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.search.submit"),
            action=ClickAction.model_construct(target=None),
        )

        first = asyncio.create_task(gateway.execute(request, context))
        await adapter.entered.wait()
        second = asyncio.create_task(
            gateway.execute(request.model_copy(update={"action_id": "action-2"}), context)
        )
        await asyncio.sleep(0)
        assert adapter.calls == ["member.search.submit"]
        release.set()
        await first
        await second
        assert adapter.calls == ["member.search.submit", "member.search.submit"]

    asyncio.run(scenario())


def test_gateway_dispatch_blocks_human_takeover_until_release(tmp_path: Path) -> None:
    async def scenario() -> None:
        release = asyncio.Event()
        adapter = RecordingSurfaceAdapter(block=release)
        gateway, controller = _gateway(adapter, _recorder(tmp_path))
        context = await _context(controller)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.search.submit"),
            action=ClickAction.model_construct(target=None),
        )

        first_task = asyncio.create_task(gateway.execute(request, context))
        await adapter.entered.wait()
        await controller.request_pause("control-1")

        try:
            await controller.grant_human_control(
                "control-1",
                operator_id="op-1",
                display_name="Alex",
            )
        except SessionControllerError as error:
            assert error.code == "ACTION_IN_FLIGHT"
        else:
            raise AssertionError("human control should be blocked while the gateway is in flight")

        second_task = asyncio.create_task(gateway.execute(request, context))
        await asyncio.sleep(0)
        assert adapter.calls == ["member.search.submit"]

        release.set()
        first_result = await first_task
        second_result = await second_task

        assert first_result.outcome == "EXECUTED"
        assert second_result.reason_code in {"STALE_GENERATION", "DISPATCH_NOT_ALLOWED"}

        state = await controller.grant_human_control(
            "control-1",
            operator_id="op-1",
            display_name="Alex",
        )
        assert state.control_state == "operator_controlled"

    asyncio.run(scenario())


def test_pre_action_evidence_failure_blocks_dispatch() -> None:
    async def scenario() -> None:
        adapter = RecordingSurfaceAdapter()
        gateway, controller = _gateway(adapter, FailingEvidenceRecorder())
        context = await _context(controller)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.search.submit"),
            action=ClickAction.model_construct(target=None),
        )

        result = await gateway.execute(request, context)

        assert result.reason_code == "EVIDENCE_PRE_ACTION_FAILED"
        assert adapter.calls == []

    asyncio.run(scenario())


def test_post_action_evidence_failure_reports_effect_may_have_occurred() -> None:
    async def scenario() -> None:
        adapter = RecordingSurfaceAdapter()
        recorder = PostDispatchFailingEvidenceRecorder()
        gateway, controller = _gateway(adapter, recorder)
        context = await _context(controller)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.search.submit"),
            action=ClickAction.model_construct(target=None),
        )

        result = await gateway.execute(request, context)

        assert result.outcome == "FAILED"
        assert result.reason_code == "ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED"
        assert adapter.calls == ["member.search.submit"]

    asyncio.run(scenario())


def test_fill_secret_is_not_persisted_in_gateway_evidence(tmp_path: Path) -> None:
    async def scenario() -> None:
        adapter = RecordingSurfaceAdapter()
        recorder = _recorder(tmp_path)
        gateway, controller = _gateway(adapter, recorder)
        context = await _context(controller)
        request = GatewayActionRequest(
            action_id="action-1",
            semantic_target=_target("member.search.member_id"),
            action=FillAction.model_construct(
                target=None, value=SecretStr("MEMBER_PRIVATE_GATEWAY_82917")
            ),
        )

        result = await gateway.execute(request, context)

        assert result.outcome == "EXECUTED"
        assert b"MEMBER_PRIVATE_GATEWAY_82917" not in recorder.path.read_bytes()

    asyncio.run(scenario())
