"""Exercise real operator controls and responsive product routes without a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    base = parser.parse_args().base_url
    output = Path("docs/references/ui/implemented/generic-discovery")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1448, "height": 1086})
        page.set_default_timeout(90_000)
        intervention_id = None
        completed = False
        try:
            page.goto(base + "/interventions")
            with page.expect_response(
                lambda response: (
                    response.url.endswith("/api/interventions")
                    and response.request.method == "POST"
                )
            ) as started:
                page.get_by_role("button", name="Start Demo Handoff").click()
            initial = started.value.json()
            intervention_id = initial["intervention_id"]
            page.get_by_alt_text("Current managed browser surface").wait_for()
            page.get_by_role("button", name="Take Control", exact=True).click()
            page.screenshot(path=output / "handoff-active.png", full_page=True)
            with page.expect_response(
                lambda response: response.url.endswith("/actions")
            ) as operated:
                page.get_by_role("button", name="Savings", exact=True).click()
            assert operated.value.json()["executed"] is True
            with page.expect_response(
                lambda response: response.url.endswith("/return-control")
            ) as returned:
                page.get_by_role("button", name="Return Control to Agent").click()
            result = returned.value.json()
            assert result["replay_result"] == "SUCCESS", result
            assert result["same_surface_session"] is True
            assert result["generation_after"] > result["generation_before"]
            assert result["repeated_automation_side_effects"] is False
            assert result["replay_model_calls"] == 0
            assert result["outputs"] == {"balance_minor_units": 98765, "currency": "USD"}
            completed = True
            page.locator(".completion-bar").wait_for()
            page.screenshot(path=output / "handoff-completed.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            checked = []
            for route in ("/", "/discover", "/capabilities", "/runs", "/interventions"):
                page.goto(base + route)
                page.locator("main").wait_for()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
                ), route
                checked.append(route)
            Path("var/manual-handoff.json").write_text(
                json.dumps(
                    {"passed": True, "handoff": result, "responsive_routes": checked}, indent=2
                ),
                encoding="utf-8",
            )
            print("HITL UI continuation and five responsive routes: PASS", flush=True)
        finally:
            if intervention_id and not completed:
                page.request.post(base + f"/api/interventions/{intervention_id}/stop")
            browser.close()


if __name__ == "__main__":
    main()
