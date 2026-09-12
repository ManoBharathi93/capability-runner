"""Capture the four P5.4b reference-defined product states with Playwright."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


def _capture(page: Page, url: str, output: Path, ready_selector: str) -> None:
    page.goto(url, wait_until="domcontentloaded")
    page.add_style_tag(
        content=(
            "*, *::before, *::after { animation: none !important; "
            "transition: none !important; }"
        )
    )
    page.locator(ready_selector).wait_for()
    page.screenshot(path=output)


def _assert_no_horizontal_overflow(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded")
    page.locator("main").wait_for()
    dimensions = page.evaluate(
        """() => ({
            viewport: document.documentElement.clientWidth,
            content: document.documentElement.scrollWidth,
        })"""
    )
    if dimensions["content"] > dimensions["viewport"]:
        raise RuntimeError(f"Horizontal overflow at {url}: {dimensions}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/references/ui/implemented"),
    )
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1448, "height": 1086})
        _capture(page, f"{arguments.base_url}/", arguments.output / "home.png", ".metric-grid")
        _capture(
            page,
            f"{arguments.base_url}/capabilities",
            arguments.output / "capability-library.png",
            ".library-layout",
        )

        page.goto(f"{arguments.base_url}/runs", wait_until="networkidle")
        run_rows = page.locator(".run-list .run-row")
        through_line_rows = run_rows.filter(has_text="through-line-")
        selected_run = through_line_rows.first if through_line_rows.count() else run_rows.first
        run_href = selected_run.get_attribute("href")
        if run_href is None:
            raise RuntimeError("A real run is required for the run-detail screenshot.")
        _capture(
            page,
            f"{arguments.base_url}{run_href}",
            arguments.output / "run-detail.png",
            ".run-detail-page",
        )

        started = page.request.post(f"{arguments.base_url}/api/interventions")
        if not started.ok:
            raise RuntimeError("A live intervention could not be started for capture.")
        intervention_id = started.json()["intervention_id"]
        intervention_url = f"{arguments.base_url}/interventions/{intervention_id}"
        try:
            _capture(
                page,
                intervention_url,
                arguments.output / "human-intervention.png",
                ".surface-frame img",
            )
        finally:
            page.request.post(
                f"{arguments.base_url}/api/interventions/{intervention_id}/stop"
            )

        page.set_viewport_size({"width": 390, "height": 844})
        for route in ("/", "/discover", "/capabilities", "/runs", "/interventions"):
            _assert_no_horizontal_overflow(page, f"{arguments.base_url}{route}")
        browser.close()


if __name__ == "__main__":
    main()