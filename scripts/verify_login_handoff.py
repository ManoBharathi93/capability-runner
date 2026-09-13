"""Headed synthetic sign-in check; automated input is not physical acceptance."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright

from demo_app.product_http import ProductWorkflowService, create_product_app
from demo_app.reviewer_runtime import serve_app


def main() -> None:
    output = Path("docs/submission/screenshots")
    output.mkdir(parents=True, exist_ok=True)
    workflow = ProductWorkflowService(
        output_root=Path("var/login-handoff-review"),
        environment_provider=lambda: {"CAPABILITY_RUNNER_BROWSER_HEADLESS": "false"},
    )
    app = create_product_app(workflows=workflow)
    with serve_app(app) as url, sync_playwright() as playwright:
        client = playwright.chromium.launch(headless=True)
        page = client.new_page(viewport={"width": 1440, "height": 1100})

        def capture(name: str) -> None:
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            page.wait_for_function("window.scrollY === 0")
            page.screenshot(path=str(output / name), full_page=True, animations="disabled")

        try:
            page.goto(f"{url}/interventions")
            page.get_by_role("button", name="Start Sign-in Handoff", exact=True).click()
            page.get_by_role("heading", name="Sign in in the managed browser").wait_for()
            identifier = page.url.rsplit("/", 1)[-1]
            live = workflow._get_live(identifier)  # pyright: ignore[reportPrivateUsage]
            state = live.execution.adapter._sessions[live.execution.session.surface_session_id]
            identity_before = live.identity_before

            async def capture_empty_login() -> None:
                await state.page.screenshot(path=str(output / "managed-sign-in.png"))

            live.runner.run(capture_empty_login())
            page.get_by_role("button", name="Take control", exact=True).click()
            page.get_by_role("button", name="Focus live browser", exact=True).wait_for()
            capture("login-handoff-human.png")

            async def synthetic_human_input() -> None:
                frame = state.page.frame_locator('iframe[name="work-area"]')
                await frame.get_by_label("Demo username").fill("demo-reviewer")
                await frame.get_by_label("Demo password").fill("demo-only")
                await frame.get_by_role("button", name="Sign in", exact=True).click()
                await frame.locator("[data-session-state]").wait_for()

            live.runner.run(synthetic_human_input())
            page.get_by_role("button", name="Return control to automation", exact=True).click()
            page.get_by_text("98765", exact=True).wait_for(timeout=60000)
            capture("login-handoff-completed.png")
            summary = json.loads((live.recorder.run_directory / "summary.json").read_text())
            assert summary["status"] == "SUCCESS"
            assert summary["outputs"] == {"balance_minor_units": 98765, "currency": "USD"}
            assert summary["identity_after"] == identity_before
            assert summary["automated_browser_action_count"] == 4
            assert summary["operator_gateway_action_count"] == 0
            assert summary["replay_model_calls"] == 0
            evidence = Path("evidence/login-handoff")
            evidence.mkdir(parents=True, exist_ok=True)
            for name in ["summary.json", "evidence.jsonl"]:
                shutil.copyfile(live.recorder.run_directory / name, evidence / name)
            check = {
                "passed": True,
                "run_id": summary["run_id"],
                "input_provenance": "automated Playwright stand-in",
                "physical_human_acceptance": "MANUAL_ACCEPTANCE_REQUIRED",
            }
            (evidence / "ui-check.json").write_text(json.dumps(check, indent=2) + "\n")
            print(json.dumps(check))
        finally:
            client.close()
            workflow.close()


if __name__ == "__main__":
    with (
        patch(
            "capability_runner.discovery.providers.openai_client.OpenAIModelClient.complete",
            side_effect=AssertionError("Unexpected model call"),
        ),
        patch(
            "capability_runner.discovery.providers.anthropic_client.AnthropicModelClient.complete",
            side_effect=AssertionError("Unexpected model call"),
        ),
        patch(
            "capability_runner.discovery.providers.gemma_client.GemmaModelClient.complete",
            side_effect=AssertionError("Unexpected model call"),
        ),
    ):
        main()
