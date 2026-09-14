from __future__ import annotations

import json
from pathlib import Path

import pytest

from capability_runner.discovery.model_client import ModelRequest, ModelResponse
from demo_app.app import create_app
from demo_app.discovery_workspace import DiscoveryWorkspace
from demo_app.reviewer_runtime import serve_app


class AdversarialModel:
    def __init__(self, mode: str) -> None:
        self.mode, self.calls, self.old_ref = mode, 0, ""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        payload = json.loads(request.messages[-1].content)
        if self.calls == 1:
            control = next(item for item in payload["elements"] if item["name"] == "Member Search")
            self.old_ref = control["ref"]
            decision = {
                "kind": "click",
                "observation_id": payload["observation_id"],
                "element_ref": control["ref"],
            }
        elif self.mode == "unchanged":
            decision = {"kind": "inspect"}
        else:
            decision = {
                "kind": "click",
                "observation_id": payload["observation_id"],
                "element_ref": self.old_ref
                if self.mode == "stale"
                else f"{payload['generation']}:e999",
            }
        return ModelResponse(content=json.dumps(decision), provider="scripted", model="adversarial")


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("unchanged", "NO_PROGRESS"),
        ("stale", "STALE_ELEMENT_REF"),
        ("unknown", "UNKNOWN_ELEMENT_REF"),
    ],
)
def test_generic_discovery_rejects_stagnation_and_invalid_current_refs(
    tmp_path: Path,
    mode: str,
    reason: str,
) -> None:
    with serve_app(create_app()) as url:
        workspace = DiscoveryWorkspace(tmp_path, lambda: {}, {"corebank": url})
        model = AdversarialModel(mode)
        try:
            status = workspace.start(
                "Please find the savings balance for member 67890.",
                "corebank",
                model=model,
            )
            run = workspace.runs[str(status["run_id"])]
            assert run.worker is not None
            run.worker.join(timeout=90)
            assert run.status == "FAILED", (run.status, run.reason_code)
            assert run.reason_code == reason
            assert run.package is None
            assert run.actions == 1  # Only the first, freshly referenced navigation was dispatched.
            assert model.calls == 2
            events = run.recorder.path.read_text()
            assert "DISCOVERY_OBSERVATION_CHANGED" in events
            assert "observation_fingerprint" in events
            assert "67890" not in events
            assert "nearby_text_summary" not in events
            assert '"elements"' not in events
            if mode == "stale":
                assert "STALE_ELEMENT_REF_REJECTED" in events
        finally:
            workspace.close()
