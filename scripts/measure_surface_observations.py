"""Measure synthetic page snapshots; no provider calls, raw page files or token estimates."""

import asyncio
import json
import sys
from pathlib import Path

from capability_runner.contracts.surfaces import ApplicationProfile
from capability_runner.discovery.browser_discovery import goal_inputs, present_browser
from capability_runner.surfaces.browser_surface_adapter import BrowserSurfaceAdapter
from demo_app.app import create_app
from demo_app.reviewer_runtime import serve_app


async def measure(url):
    adapter = BrowserSurfaceAdapter(default_timeout_ms=10000)
    profile = ApplicationProfile(
        profile_id="measure",
        application_family="measure",
        variant="unprofiled",
        entry_point=url,
        discovery_only=True,
    )
    result = []
    try:
        session = await adapter.open_surface_session(profile)
        page = adapter._sessions[session.surface_session_id].page
        for name, route in [
            ("search", "/workspace"),
            ("details", "/members/67890"),
            ("account", "/members/67890/accounts/savings"),
        ]:
            frame = page.frame(name="work-area")
            await frame.goto(url.rstrip("/") + route)
            obs = await adapter.observe_browser(session)
            goal = "Please find the savings balance for member 67890."
            payload = present_browser(goal, obs, goal_inputs(goal), [], None).messages[-1].content
            result.append(
                {
                    "page": name,
                    "normalized_characters": len(obs.model_dump_json()),
                    "model_characters": len(payload),
                    "model_bytes": len(payload.encode()),
                    "elements": len(obs.elements),
                    "interactive_elements": sum(e.action_kind is not None for e in obs.elements),
                    "text_characters": sum(
                        len(e.text) + len(e.nearby_text_summary) for e in obs.elements
                    ),
                }
            )
    finally:
        await adapter.aclose()
    return result


with serve_app(create_app()) as url:
    result = asyncio.run(measure(url))
Path(sys.argv[1]).write_text(json.dumps(result, indent=2))
print(json.dumps(result))
