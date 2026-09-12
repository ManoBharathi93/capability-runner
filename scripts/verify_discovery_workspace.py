"""Exercise the actual product UI with a real provider and capture selected reviewer states."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--application", choices=("corebank-known", "bank-b"), required=True)
    arguments = parser.parse_args()
    base = arguments.base_url
    app = arguments.application
    goal = (
        "Open member 67890 and tell me how much is in their Savings account."
        if app == "corebank-known"
        else "Find the savings balance for customer 67890."
    )
    output = Path("docs/references/ui/implemented/generic-discovery")
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"application": app, "checks": {}, "passed": False}
    report_path = Path("var") / f"manual-{app}.json"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1448, "height": 1086})
        page.set_default_timeout(90_000)
        try:
            page.goto(base + "/discover", wait_until="domcontentloaded")
            page.get_by_label("Application", exact=True).select_option(app)
            page.get_by_label("Workflow goal").fill(goal)
            assert page.get_by_role("button", name="Discover Capability").is_enabled()
            with page.expect_response(
                lambda response: response.url.endswith("/api/discovery")
            ) as submitted:
                page.get_by_role("button", name="Discover Capability").click()
            status = submitted.value.json()
            run_id = status["run_id"]
            report["run_id"] = run_id
            print(f"UI Discovery started: {run_id}", flush=True)
            session_ids: set[str] = set()
            hashes: set[str] = set()
            deadline = time.monotonic() + 330
            captured = False
            while time.monotonic() < deadline:
                page.wait_for_timeout(1000)
                status = page.request.get(base + f"/api/discovery/{run_id}").json()
                if status["session_id"]:
                    session_ids.add(status["session_id"])
                preview = page.get_by_alt_text(
                    "Live legacy application in the current Discovery session"
                )
                if preview.is_visible():
                    hashes.add(hashlib.sha256(preview.screenshot()).hexdigest())
                    if not captured:
                        page.screenshot(path=output / f"{app}-live.png")
                        captured = True
                if status["status"] != "RUNNING":
                    break
            report.update(
                status=status["status"],
                reason_code=status["reason_code"],
                model_calls=status["model_calls"],
                same_session=len(session_ids) == 1,
                distinct_visible_frames=len(hashes),
                live_visible=captured,
            )
            assert status["status"] == "SUCCESS", status["reason_code"]
            assert len(session_ids) == 1 and len(hashes) >= 2
            page.get_by_text("CAPABILITY CREATED", exact=True).wait_for()
            page.screenshot(path=output / f"{app}-complete.png", full_page=True)
            replay_form = page.locator(".discovery-replay")
            replay_form.locator("input").fill("12345")
            with page.expect_response(
                lambda response: response.url.endswith(f"/{run_id}/replay")
            ) as replayed:
                replay_form.get_by_role("button", name="Run Replay").click()
            replay = replayed.value.json()
            assert replay["outcome"] == "SUCCESS", replay
            assert replay["outputs"] == {"balance_minor_units": 438221, "currency": "USD"}
            assert replay["replay_model_calls"] == 0
            page.locator(".replay-outcome").wait_for()
            page.locator(".replay-outcome").scroll_into_view_if_needed()
            page.screenshot(path=output / f"{app}-replay.png", full_page=True)
            report["replay"] = replay
            if app == "corebank-known":
                replay_form.locator("input").fill("00000")
                with page.expect_response(
                    lambda response: response.url.endswith(f"/{run_id}/replay")
                ) as exceptional:
                    replay_form.get_by_role("button", name="Run Replay").click()
                outcome = exceptional.value.json()
                assert outcome["business_outcome_code"] == "MEMBER_NOT_FOUND", outcome
                page.get_by_text("MEMBER_NOT_FOUND", exact=True).wait_for()
                page.screenshot(path=output / "business-outcome.png", full_page=True)
                report["business_outcome"] = outcome["business_outcome_code"]
            report["passed"] = True
            print(f"UI acceptance: PASS ({len(hashes)} distinct rendered live frames)", flush=True)
        finally:
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            browser.close()


if __name__ == "__main__":
    main()
