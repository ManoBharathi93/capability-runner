"""Thin local product composition: active Discovery, ephemeral views, reusable packages."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from capability_runner.application.demo_configuration import (
    build_core_bank_demo_profile,
    build_demo_automation_policy,
    build_demo_capability_request,
    trusted_success_targets,
)
from capability_runner.bootstrap import replay_package
from capability_runner.capabilities.binding_compiler import compile_package
from capability_runner.capabilities.capability_builder import CapabilityBuilder
from capability_runner.capabilities.capability_store import CapabilityStore
from capability_runner.contracts.browser_discovery import (
    ApplicationIdentity,
    BrowserScope,
    CapabilityPackage,
)
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.contracts.gateway import GatewayExecutionContext
from capability_runner.contracts.policy import PolicyDefinition
from capability_runner.contracts.requests import DiscoveryRequest
from capability_runner.contracts.surfaces import ApplicationProfile, SurfaceSessionRef
from capability_runner.contracts.targets import UrlTarget
from capability_runner.discovery.browser_discovery import goal_inputs
from capability_runner.discovery.configuration import (
    create_model_client,
    load_model_provider_config,
)
from capability_runner.discovery.discovery_engine import DiscoveryEngine
from capability_runner.discovery.model_client import ModelClient, ModelRequest, ModelResponse
from capability_runner.discovery.snapshot_collector import DiscoverySnapshotCollector
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from capability_runner.evidence.redaction import RedactionContext
from capability_runner.interaction.action_gateway import ActionGateway
from capability_runner.interaction.policy_guard import PolicyGuard
from capability_runner.interaction.session_controller import SessionController
from capability_runner.interfaces.async_core_runner import AsyncCoreRunner
from capability_runner.surfaces.browser_observation import fingerprint, origin_of, within_scope
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter


@dataclass
class WorkspaceRun:
    run_id: str
    application: str
    runner: AsyncCoreRunner
    recorder: EvidenceRecorder
    scope: BrowserScope
    status: str = "RUNNING"
    reason_code: str | None = None
    model_calls: int = 0
    actions: int = 0
    adapter: BrowserSurfaceAdapter | None = None
    session: SurfaceSessionRef | None = None
    package: CapabilityPackage | None = None
    worker: threading.Thread | None = None
    replay_results: list[dict[str, object]] = field(default_factory=list)


class DiscoveryWorkspace:
    def __init__(
        self,
        root: Path,
        environment: Callable[[], Mapping[str, str]],
        target_urls: Mapping[str, str] | None = None,
    ) -> None:
        self.root, self.environment = root, environment
        self.target_urls = dict(
            target_urls
            or {
                "corebank": "http://127.0.0.1:5001/",
                "bank-b": "http://127.0.0.1:5002/",
            }
        )
        self.runs: dict[str, WorkspaceRun] = {}
        self.lock = threading.Lock()

    def start(
        self,
        goal: str,
        application: str,
        url: str | None = None,
        *,
        model: ModelClient | None = None,
    ) -> dict[str, object]:
        if not goal.strip() or len(goal) > 4000:
            raise ValueError("INVALID_GOAL")
        environment = self.environment()
        if application == "new":
            entry = url or ""
        else:
            entry = self.target_urls.get(
                "corebank" if application == "corebank-known" else application, ""
            )
        allowed_urls = list(self.target_urls.values())
        configured = environment.get("CAPABILITY_RUNNER_READ_ONLY_URLS", "[]")
        allowed_urls.extend(json.loads(configured))
        if urlsplit(entry).query or not any(
            within_scope(
                entry,
                BrowserScope(origin=origin_of(item), read_only_paths=(urlsplit(item).path or "/",)),
            )
            for item in allowed_urls
        ):
            raise ValueError("APPLICATION_NOT_ALLOWED")
        scope_entry = next(
            item
            for item in allowed_urls
            if within_scope(
                entry,
                BrowserScope(origin=origin_of(item), read_only_paths=(urlsplit(item).path or "/",)),
            )
        )
        scope = BrowserScope(
            origin=origin_of(entry),
            read_only_paths=(urlsplit(scope_entry).path or "/",),
            read_only_post_paths=("/members/search",)
            if application in {"corebank", "corebank-known"}
            else (),
        )
        # Fail configuration validation before starting a managed browser.
        config = (
            load_model_provider_config(environment).model_copy(update={"timeout_seconds": 60})
            if model is None
            else None
        )
        with self.lock:
            if any(run.status == "RUNNING" for run in self.runs.values()):
                raise ValueError("DISCOVERY_ALREADY_RUNNING")
            if len(self.runs) >= 8:
                raise ValueError("SESSION_LIMIT_REACHED")
            run_id = "discovery-" + uuid4().hex
            values = frozenset(
                goal[item.source.start : item.source.end] for item in goal_inputs(goal)
            )
            recorder = EvidenceRecorder(
                self.root, run_id, redaction_context=RedactionContext(explicit_values=values)
            )
            run = WorkspaceRun(
                run_id, application, AsyncCoreRunner(timeout_seconds=360), recorder, scope
            )
            self.runs[run_id] = run

        def work() -> None:
            client = model
            try:
                if client is None:
                    assert config is not None
                    client = create_model_client(config)

                class CountedClient:
                    async def complete(self, request: ModelRequest) -> ModelResponse:
                        run.model_calls += 1
                        assert client is not None
                        return await client.complete(request)

                run.runner.run(self._discover(run, goal, entry, CountedClient()))
            except Exception as error:
                run.status = "FAILED"
                # Exception text may contain provider/URL data. Persist only a bounded code.
                code = str(error)
                run.reason_code = (
                    code
                    if code.isupper() and code.replace("_", "").isalpha()
                    else "DISCOVERY_FAILED"
                )
            finally:
                if client is not None and hasattr(client, "aclose"):
                    try:
                        run.runner.run(client.aclose())  # type: ignore[attr-defined]
                    except Exception:
                        pass
                self._summary(run)

        run.worker = threading.Thread(target=work, daemon=True)
        run.worker.start()
        return self.status(run_id)

    async def _discover(self, run: WorkspaceRun, goal: str, entry: str, model: ModelClient) -> None:
        known = run.application == "corebank-known"
        profile = (
            build_core_bank_demo_profile(entry)
            if known
            else ApplicationProfile.model_validate(
                {
                    "profile_id": "new-application",
                    "application_family": "new-application",
                    "variant": "unprofiled",
                    "entry_point": entry,
                    "discovery_only": True,
                }
            )
        )
        adapter = BrowserSurfaceAdapter(default_timeout_ms=10_000)
        run.adapter = adapter
        run.session = await adapter.open_surface_session(profile, browser_scope=run.scope)
        controller = SessionController()
        await controller.open_session(session_id=run.run_id, run_id=run.run_id)
        context = GatewayExecutionContext(
            run_id=run.run_id,
            control_session_id=run.run_id,
            expected_generation=0,
            surface_session=run.session,
            profile=profile,
        )
        gateway = ActionGateway(
            policy_guard=PolicyGuard(
                build_demo_automation_policy(require_savings_approval=False)
                if known
                else PolicyDefinition(policy_id="deny", version="1")
            ),
            session_controller=controller,
            surface_adapter=adapter,
            evidence_recorder=run.recorder,
            observation_adapter=adapter,
            browser_scope=run.scope,
        )
        engine = DiscoveryEngine(
            model_client=model,
            action_gateway=gateway,
            snapshot_collector=DiscoverySnapshotCollector(adapter),
            evidence_recorder=run.recorder,
        )
        request = DiscoveryRequest(
            goal=goal,
            target=UrlTarget(url=profile.entry_point),
            required_completion_targets=trusted_success_targets() if known else (),
        )
        try:
            initial = await adapter.observe_browser(run.session)
            if known:
                result = await engine.discover(request, context)
                run.actions = result.actions
                if result.outcome != "SUCCESS":
                    run.status, run.reason_code = result.outcome, result.reason_code
                    return
                definition = (
                    CapabilityBuilder().build(build_demo_capability_request(result)).definition
                )
                definition = definition.model_copy(
                    update={"capability_id": "workflow_" + run.run_id[-16:]}
                )
                identity = ApplicationIdentity(
                    origin=initial.origin,
                    entry_path=initial.path,
                    title=initial.title,
                    fingerprint=fingerprint(initial.origin + initial.path + initial.title),
                )
                package = CapabilityPackage(
                    capability=definition,
                    profile=profile,
                    identity=identity,
                    binding_evidence=(),
                    entry_point=profile.entry_point,
                )
            else:
                discovered = await engine.discover_unprofiled(request, context, adapter)
                result = discovered.result
                run.actions = result.actions
                if result.outcome != "SUCCESS":
                    run.status, run.reason_code = result.outcome, result.reason_code
                    return
                inputs = {
                    item.input_ref: goal[item.source.start : item.source.end]
                    for item in goal_inputs(goal)
                }
                runtime_values = {
                    target.rsplit(".", 1)[-1]: inputs[ref]
                    for ref, target in discovered.input_targets.items()
                }
                package = compile_package(
                    discovered,
                    entry_point=entry,
                    capability_id="workflow_" + run.run_id[-16:],
                    runtime_values=runtime_values,
                )
            store = CapabilityStore(run.recorder.run_directory / "capabilities")
            store.save_package(package)
            # Also expose the normal capability JSON to the existing artifact library.
            from capability_runner.capabilities.capability_validator import CapabilityValidator

            store.save(CapabilityValidator().validate(package.capability))
            run.package = store.load_package(package.capability.capability_id, "1.0.0")
            for code in ("CAPABILITY_VALIDATED", "CAPABILITY_STORED"):
                run.recorder.record(
                    EvidenceEvent(
                        event_type="lifecycle",
                        component="discovery-workspace",
                        run_id=run.run_id,
                        session_id=run.run_id,
                        reason_code=code,
                        outcome="completed",
                    )
                )
            run.status, run.reason_code = "SUCCESS", "COMPLETED"
        finally:
            await controller.stop_session(run.run_id)

    def status(self, run_id: str) -> dict[str, object]:
        run = self.runs[run_id]
        events = []
        if run.recorder.path.is_file():
            for line in run.recorder.path.read_text(encoding="utf-8").splitlines()[-100:]:
                try:
                    events.append(json.loads(line))
                except ValueError:
                    continue
        return {
            "run_id": run_id,
            "status": run.status,
            "reason_code": run.reason_code,
            "application": run.application,
            "model_calls": run.model_calls,
            "actions": run.actions,
            "session_id": run.session.surface_session_id if run.session else None,
            "view_available": run.session is not None,
            "events": events,
            "capability": run.package.capability.model_dump(mode="json") if run.package else None,
            "binding": run.package.profile.model_dump(mode="json") if run.package else None,
            "binding_evidence": [item.model_dump() for item in run.package.binding_evidence]
            if run.package
            else [],
            "replays": run.replay_results,
        }

    def view(self, run_id: str) -> bytes:
        run = self.runs[run_id]
        if run.adapter is None or run.session is None:
            raise ValueError("VIEW_NOT_READY")
        return run.runner.run(run.adapter.capture_view(run.session)).content

    def replay(self, run_id: str, inputs: Mapping[str, str]) -> dict[str, object]:
        run = self.runs[run_id]
        if run.package is None:
            raise ValueError("CAPABILITY_NOT_READY")
        package = CapabilityStore(run.recorder.run_directory / "capabilities").load_package(
            run.package.capability.capability_id, "1.0.0"
        )
        replay_id = "replay-" + uuid4().hex
        recorder = EvidenceRecorder(
            self.root,
            replay_id,
            redaction_context=RedactionContext(explicit_values=frozenset(inputs.values())),
        )
        result = run.runner.run(
            replay_package(package, inputs, scope=run.scope, recorder=recorder, run_id=replay_id)
        )
        payload: dict[str, object] = {
            **result.model_dump(mode="json"),
            "replay_model_calls": 0,
            "fresh_browser": True,
        }
        run.replay_results.append(payload)
        return payload

    def _summary(self, run: WorkspaceRun) -> None:
        payload = {
            "schema_version": 1,
            "run_id": run.run_id,
            "demo_kind": "discovery",
            "status": run.status,
            "discovery_result": run.status,
            "failure_reason": run.reason_code,
            "discovery_model_calls": run.model_calls,
            "browser_action_count": run.actions,
            "capability_id": run.package.capability.capability_id if run.package else None,
            "capability_version": "1.0.0" if run.package else None,
        }
        (run.recorder.run_directory / "summary.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def replay_stored(
        self, capability_id: str, version: str, inputs: Mapping[str, str]
    ) -> dict[str, object]:
        if not re.fullmatch(r"workflow_[a-f0-9]{16}", capability_id) or version != "1.0.0":
            raise ValueError("INVALID_CAPABILITY")
        candidates = list(
            self.root.glob(f"*/capabilities/{capability_id}/{version}.package/metadata.json")
        )
        if len(candidates) != 1:
            raise ValueError("CAPABILITY_NOT_FOUND")
        store = CapabilityStore(candidates[0].parents[2])
        package = store.load_package(capability_id, version)
        entry = str(package.profile.entry_point)
        allowed = [
            *self.target_urls.values(),
            *json.loads(self.environment().get("CAPABILITY_RUNNER_READ_ONLY_URLS", "[]")),
        ]
        root = next(
            (
                item
                for item in allowed
                if within_scope(
                    entry,
                    BrowserScope(
                        origin=origin_of(item), read_only_paths=(urlsplit(item).path or "/",)
                    ),
                )
            ),
            None,
        )
        if root is None:
            raise ValueError("APPLICATION_NOT_ALLOWED")
        scope = BrowserScope(
            origin=origin_of(root),
            read_only_paths=(urlsplit(root).path or "/",),
            read_only_post_paths=("/members/search",)
            if root == self.target_urls.get("corebank")
            else (),
        )
        run_id = "replay-" + uuid4().hex
        recorder = EvidenceRecorder(
            self.root,
            run_id,
            redaction_context=RedactionContext(explicit_values=frozenset(inputs.values())),
        )
        with AsyncCoreRunner(timeout_seconds=180) as runner:
            result = runner.run(
                replay_package(package, inputs, scope=scope, recorder=recorder, run_id=run_id)
            )
        summary = {
            "schema_version": 1,
            "run_id": run_id,
            "demo_kind": "replay",
            "capability_id": capability_id,
            "capability_version": version,
            "status": result.outcome,
            "replay_result": result.outcome,
            "business_outcome": result.business_outcome_code,
            "failure_reason": result.reason_code,
            "replay_model_calls": 0,
            "fresh_replay_session": True,
            "outputs": {
                key: value
                for key, value in result.outputs.items()
                if any(
                    output.name == key and output.value_type in {"INTEGER", "CURRENCY_CODE"}
                    for output in package.capability.outputs
                )
            },
        }
        (recorder.run_directory / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return summary

    def close(self) -> None:
        for run in self.runs.values():
            if run.adapter is not None:
                try:
                    run.runner.run(run.adapter.aclose())
                except Exception:
                    pass
            run.runner.close()
