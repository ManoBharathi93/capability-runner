"""Opt-in real-provider acceptance. Records safe metadata, never prompts or responses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from capability_runner.discovery.browser_discovery import DECISIONS
from capability_runner.discovery.configuration import (
    create_model_client,
    load_model_provider_config,
)
from capability_runner.discovery.model_client import ModelRequest, ModelResponse
from demo_app.app import create_app
from demo_app.cli import _load_environment
from demo_app.discovery_workspace import DiscoveryWorkspace
from demo_app.reviewer_runtime import serve_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--output-root", type=Path, default=Path("var/observation-acceptance"))
    args = parser.parse_args()
    environment = _load_environment()
    config = load_model_provider_config(environment)
    provider = create_model_client(config)
    observations: list[dict[str, object]] = []

    class MeasuredClient:
        calls = 0

        async def complete(self, request: ModelRequest) -> ModelResponse:
            self.calls += 1
            content = request.messages[-1].content
            current = json.loads(content)
            response = await provider.complete(request)
            decision_text = response.content.strip()
            if decision_text.startswith("```json") and decision_text.endswith("```"):
                decision_text = decision_text[7:-3].strip()
            row = {
                "generation": current["generation"],
                "element_count": len(current["elements"]),
                "model_characters": len(content),
                "model_bytes": len(content.encode()),
                "truncated": current["truncated"],
                "change_summary": current["change_summary"],
            }
            try:
                decision = DECISIONS.validate_json(decision_text).model_dump()
                refs = [decision["element_ref"]] if "element_ref" in decision else []
                refs.extend(decision.get("evidence_refs", []))
                refs.extend(decision.get("identity_refs", {}).values())
                refs.extend(item["evidence_ref"] for item in decision.get("outputs", []))
                available = {item["ref"] for item in current["elements"]}
                row.update(
                    decision_kind=decision["kind"],
                    reference_count=len(refs),
                    current_refs_only=all(ref in available for ref in refs),
                    observation_id_matches=(
                        decision.get("observation_id", current["observation_id"])
                        == current["observation_id"]
                    ),
                )
            except ValueError:
                row.update(decision_kind="INVALID_MODEL_RESPONSE", current_refs_only=False)
            observations.append(row)
            print(
                f"Observed generation {current['generation']}: {row['decision_kind']}", flush=True
            )
            return response  # No action, prompt or response substitution.

        async def aclose(self) -> None:
            if hasattr(provider, "aclose"):
                await provider.aclose()

    model = MeasuredClient()
    args.output_root.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"passed": False, "provider": config.provider}
    with serve_app(create_app()) as url:
        workspace = DiscoveryWorkspace(args.output_root, lambda: environment, {"corebank": url})
        try:
            status = workspace.start(
                "For member 67890, find their Savings account and read the current balance.",
                "corebank",
                model=model,
            )
            run = workspace.runs[str(status["run_id"])]
            assert run.worker is not None
            run.worker.join(timeout=330)
            report.update(
                discovery_run_id=run.run_id,
                discovery_status=run.status,
                discovery_reason=run.reason_code,
                discovery_model_calls=model.calls,
                observations=observations,
            )
            assert run.status == "SUCCESS", run.reason_code
            assert run.package is not None
            calls = model.calls
            input_name = run.package.capability.inputs[0].name
            replay = workspace.replay(run.run_id, {input_name: "12345"})
            expected = {"balance_minor_units": 438221, "currency": "USD"}
            # The compiler permits extra observed outputs. Verify the known optional category too.
            if "account_type" in replay["outputs"]:
                expected["account_type"] = "Savings"
            report.update(
                replay=replay, expected_outputs=expected, model_calls_after_replay=model.calls
            )
            assert replay["outcome"] == "SUCCESS" and replay["outputs"] == expected, replay[
                "outcome"
            ]
            assert model.calls == calls and replay["replay_model_calls"] == 0
            assert all(item["current_refs_only"] for item in observations)
            assert all(item["observation_id_matches"] for item in observations)
            assert [item["generation"] for item in observations] == sorted(
                {item["generation"] for item in observations}
            )
            report.update(
                replay=replay,
                expected_outputs=expected,
                model_calls_after_replay=model.calls,
                passed=True,
            )
        finally:
            (args.output_root / "summary.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            workspace.close()
    print("Surface observation live acceptance: PASS", flush=True)


if __name__ == "__main__":
    main()
