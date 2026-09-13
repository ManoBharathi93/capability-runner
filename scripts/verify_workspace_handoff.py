"""Automated direct-browser stand-in; this is NOT physical human acceptance.

Starts an isolated product instance so the test can hold the actual managed Page
without adding a browser-driving endpoint to the product. --headed shows that
same browser. Requires a built frontend; no model configuration is read.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from demo_app.discovery_workspace import DiscoveryWorkspace
from demo_app.product_artifacts import ProductArtifactIndex
from demo_app.product_http import ProductWorkflowService, create_product_app
from demo_app.reviewer_runtime import serve_app


def capture(page: object, path: Path) -> None:
    # Page is the review client, not the retained application browser.
    from playwright.sync_api import Page

    assert isinstance(page, Page)
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    page.wait_for_function("window.scrollY === 0")
    page.screenshot(path=path, full_page=True, animations="disabled")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    output = Path("docs/submission/screenshots")
    output.mkdir(parents=True, exist_ok=True)
    runtime = Path("var/direct-browser-review")
    workflow = ProductWorkflowService(
        output_root=runtime,
        environment_provider=lambda: {
            "CAPABILITY_RUNNER_BROWSER_HEADLESS": "false" if args.headed else "true",
        },
    )
    workspace = DiscoveryWorkspace(runtime / "discovery", lambda: {})
    app = create_product_app(
        workflows=workflow,
        workspace=workspace,
        artifact_index=ProductArtifactIndex(runtime_root=runtime, curated_root=Path("evidence")),
    )
    try:
        with serve_app(app) as base, sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1448, "height": 1086})
            page.set_default_timeout(90_000)
            page.goto(base + "//interventions")
            page.get_by_role("button", name="Start Demo Handoff").wait_for()
            assert page.url == base + "/interventions"
            with page.expect_response(
                lambda r: r.url.endswith("/api/interventions") and r.request.method == "POST"
            ) as response:
                page.get_by_role("button", name="Start Demo Handoff").click()
            initial = response.value.json()
            identifier = initial["intervention_id"]
            live = workflow._get_live(identifier)  # pyright: ignore[reportPrivateUsage]
            execution = live.execution
            original = execution.adapter._sessions[execution.session.surface_session_id]
            actual_page, actual_context = original.page, original.context
            page.get_by_role("button", name="Take control", exact=True).wait_for()
            capture(page, output / "handoff-paused.png")
            with page.expect_response(lambda r: r.url.endswith("/take-control")):
                page.get_by_role("button", name="Take control", exact=True).click()
            page.get_by_role("button", name="Focus live browser").wait_for()
            capture(page, output / "handoff-human.png")
            page.get_by_role("link", name="Sessions", exact=True).click()
            page.locator(f'a.run-row[href="/interventions/{identifier}"]').wait_for()
            capture(page, output / "sessions-human.png")
            page.locator(f'a.run-row[href="/interventions/{identifier}"]').click()

            async def native_action() -> None:
                # Test-only direct input, deliberately outside either gateway.
                await actual_page.screenshot(path=str(output / "managed-browser-before.png"))
                await (
                    actual_page.frame_locator('iframe[name="work-area"]')
                    .get_by_role("row")
                    .filter(has_text="Savings")
                    .get_by_role("link", name="Open", exact=True)
                    .click()
                )
                await (
                    actual_page.frame_locator('iframe[name="work-area"]')
                    .get_by_role("heading", name="Savings Account")
                    .wait_for()
                )
                await actual_page.screenshot(path=str(output / "managed-browser-after.png"))
                assert original.page is actual_page and original.context is actual_context

            live.runner.run(native_action())
            with page.expect_response(lambda r: r.url.endswith("/return-control")) as response:
                page.get_by_role("button", name="Return control to automation").click()
            result = response.value.json()
            assert result["status"] == "SUCCESS", result
            assert result["identity_before"] == result["identity_after"]
            assert result["generation_before"] == 0 and result["generation_after"] == 3
            assert result["outputs"] == {"balance_minor_units": 98765, "currency": "USD"}
            assert result["automated_browser_action_count"] == 3
            assert result["operator_gateway_action_count"] == 0
            assert result["replay_model_calls"] == 0
            assert original.page is actual_page and original.context is actual_context
            page.get_by_text("Fresh browser validation passed.", exact=False).wait_for()
            capture(page, output / "handoff-completed.png")
            page.get_by_role("link", name="Sessions", exact=True).click()
            page.get_by_text("No active sessions").wait_for()
            page.set_viewport_size({"width": 390, "height": 844})
            routes = ["/", "/discover", "/capabilities", "/runs", "/interventions", "/sessions"]
            for route in routes:
                page.goto(base + route)
                page.locator("main").wait_for()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
                ), route
            summary = {
                "passed": True,
                "acceptance_source": "automated_direct_page_stand_in",
                "physical_human_acceptance": "MANUAL_ACCEPTANCE_REQUIRED",
                "handoff": result,
                "responsive_routes": routes,
            }
            Path("var/direct-browser-ui.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
            print(
                "Direct-browser UI, identity, resume and responsive checks: PASS; "
                "physical acceptance still required."
            )
            browser.close()
    finally:
        workflow.close()
        workspace.close()


if __name__ == "__main__":
    main()
