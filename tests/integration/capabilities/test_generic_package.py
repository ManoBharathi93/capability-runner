from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import HttpUrl

from capability_runner.bootstrap import replay_package
from capability_runner.contracts.evidence import EvidenceEvent
from capability_runner.evidence.evidence_recorder import EvidenceRecorder
from demo_app.discovery_workspace import DiscoveryWorkspace
from demo_app.legacy_bank_b import create_app
from demo_app.reviewer_runtime import serve_app
from tests.fakes.browser_model import BankingBrowserModel


@pytest.mark.parametrize(
    "product,expected_outputs",
    [
        ("savings", {"balance_minor_units": 438221, "currency": "USD"}),
        ("checking", {"balance_minor_units": 15840, "currency": "USD"}),
    ],
)
def test_unprofiled_discovery_compiles_and_fresh_replay_has_no_model(
    tmp_path: Path, product: str, expected_outputs: dict[str, str | int]
) -> None:
    with serve_app(create_app()) as url:
        workspace = DiscoveryWorkspace(tmp_path, lambda: {}, {"bank-b": url})
        model = BankingBrowserModel(product=product)
        try:
            status = workspace.start(
                f"Find the {product} balance for customer 67890.", "bank-b", model=model
            )
            run = workspace.runs[str(status["run_id"])]
            assert run.worker is not None
            run.worker.join(timeout=150)
            assert run.status == "SUCCESS", (run.reason_code, workspace.status(run.run_id))
            assert run.package is not None
            assert run.package.binding_evidence
            assert not run.package.profile.discovery_only
            calls = model.calls
            name = run.package.capability.inputs[0].name
            result = workspace.replay(run.run_id, {name: "12345"})
            assert result["outcome"] == "SUCCESS", result
            # Independent fixture oracle: neither the model nor the generated artifact supplies it.
            assert result["outputs"] == expected_outputs
            assert result["replay_model_calls"] == 0
            assert model.calls == calls
            stored = DiscoveryWorkspace(tmp_path, lambda: {}, {"bank-b": url})
            try:
                replayed = stored.replay_stored(
                    run.package.capability.capability_id, "1.0.0", {name: "12345"}
                )
                assert replayed["replay_result"] == "SUCCESS"
                assert replayed["outputs"] == expected_outputs
                assert replayed["replay_model_calls"] == 0
                assert model.calls == calls
            finally:
                stored.close()
            payload = run.package.model_dump_json()
            assert not re.search(r'"[1-9][0-9]*:e[1-9][0-9]*"', payload)
            assert "67890" not in payload
            assert "987.65" not in payload
            assert "51.20" not in payload
            assert "locator_candidates" not in run.package.capability.model_dump_json()
            changed_profile = run.package.profile.model_copy(
                update={"entry_point": HttpUrl(url + "/enquiry")}
            )
            wrong_app = run.package.model_copy(update={"profile": changed_profile})
            mismatch = run.runner.run(
                replay_package(
                    wrong_app,
                    {name: "12345"},
                    scope=run.scope,
                    recorder=EvidenceRecorder(tmp_path, "mismatch"),
                    run_id="mismatch",
                )
            )
            assert mismatch.reason_code == "APPLICATION_MISMATCH"
            assert mismatch.steps_attempted == 0

        finally:
            workspace.close()


@pytest.mark.parametrize(
    "mode,reason,goal_product,model_product",
    [
        ("injection", "POLICY_DENIED", "savings", "savings"),
        ("wrong_entity", "WRONG_ENTITY", "savings", "savings"),
        ("normal", "COMPLETION_CONTEXT_MISSING", "checking", "savings"),
        ("normal", "COMPLETION_CONTEXT_MISSING", "savings", "checking"),
    ],
)
def test_unprofiled_safety_never_compiles_false_success(
    tmp_path: Path, mode: str, reason: str, goal_product: str, model_product: str
) -> None:
    with serve_app(create_app(mode=mode)) as url:
        workspace = DiscoveryWorkspace(tmp_path, lambda: {}, {"bank-b": url})
        try:
            status = workspace.start(
                f"Find the {goal_product} balance for customer 67890.",
                "bank-b",
                model=BankingBrowserModel(product=model_product, unsafe=mode == "injection"),
            )
            run = workspace.runs[str(status["run_id"])]
            assert run.worker is not None
            run.worker.join(timeout=150)
            assert run.status == "FAILED"
            assert run.reason_code == reason
            assert run.package is None
            if mode == "injection":
                events = [
                    EvidenceEvent.model_validate_json(line)
                    for line in run.recorder.path.read_text().splitlines()
                ]
                assert not any(event.outcome == "executed" for event in events)

        finally:
            workspace.close()
