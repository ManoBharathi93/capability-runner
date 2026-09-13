"""Synthetic sign-in uses the same browser; input here is an automated stand-in."""

import json
from collections import Counter
from pathlib import Path

import pytest

from capability_runner.application.operator_console import OperatorConsoleError
from demo_app.app import DemoScenario, create_app
from demo_app.product_http import ProductWorkflowService, create_product_app


@pytest.mark.parametrize("action", ["signed_in", "wrong_password", "unchanged", "closed"])
def test_sign_in_handoff_requires_authenticated_state(
    tmp_path: Path,
    action: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def forbidden(*args: object, **kwargs: object) -> None:
        calls.append("model")
        raise AssertionError("Sign-in and Replay must not call a model")

    for module, client in [("openai", "OpenAI"), ("anthropic", "Anthropic"), ("gemma", "Gemma")]:
        monkeypatch.setattr(
            f"capability_runner.discovery.providers.{module}_client.{client}ModelClient.complete",
            forbidden,
        )
    service = ProductWorkflowService(
        output_root=tmp_path,
        environment_provider=lambda: {"CAPABILITY_RUNNER_BROWSER_HEADLESS": "true"},
    )
    try:
        api = create_product_app(workflows=service).test_client()
        started_response = api.post("/api/interventions", json={"handoff_kind": "sign_in"})
        assert started_response.status_code == 201
        started = started_response.get_json()
        identifier = started["intervention_id"]
        assert started["blocked_action"] == "session.sign_in"
        assert started["generation"] == 1
        assert started["capability_id"] == "lookup_savings_after_sign_in"
        assert api.post("/api/interventions").status_code == 409
        live = service._get_live(identifier)  # pyright: ignore[reportPrivateUsage]
        execution = live.execution
        state = execution.adapter._sessions[execution.session.surface_session_id]
        page, context = state.page, state.context
        assert execution.automation_counter.executed == Counter()
        assert api.get(f"/api/interventions/{identifier}/view").status_code == 409
        granted = service.take_control(identifier)
        assert granted["generation"] == 2

        async def input_in_original_browser() -> None:
            if action == "closed":
                await page.close()
            elif action != "unchanged":
                frame = page.frame_locator('iframe[name="work-area"]')
                await frame.get_by_label("Demo username").fill("demo-reviewer")
                await frame.get_by_label("Demo password").fill(
                    "demo-only" if action == "signed_in" else "private-wrong-password-canary"
                )
                await frame.get_by_role("button", name="Sign in", exact=True).click()
                if action == "signed_in":
                    await frame.locator("[data-session-state]").wait_for()
                else:
                    assert "Sign-in failed" in await frame.get_by_role("alert").inner_text()
            assert state.page is page and state.context is context

        live.runner.run(input_in_original_browser())
        result = service.return_control(identifier)
        assert not calls
        assert result["operator_gateway_action_count"] == 0
        assert result["replay_model_calls"] == 0
        assert not result["repeated_automation_side_effects"]
        if action == "signed_in":
            assert result["status"] == "SUCCESS"
            assert result["outputs"] == {"balance_minor_units": 98765, "currency": "USD"}
            assert result["identity_before"] == result["identity_after"]
            assert result["generation_after"] == 3
            assert execution.automation_counter.executed == Counter(
                {
                    "member.search.member_id": 1,
                    "member.search.submit": 1,
                    "member.results.open": 1,
                    "member.accounts.savings": 1,
                }
            )
        else:
            assert result["status"] != "SUCCESS"
            assert result["outputs"] == {}
            assert execution.automation_counter.executed == Counter()
        with pytest.raises(OperatorConsoleError):
            service.return_control(identifier)
        events = (live.recorder.run_directory / "evidence.jsonl").read_text(encoding="utf-8")
        assert "private-wrong-password-canary" not in events
        assert "demo-only" not in events
        assert "demo-reviewer" not in events
        assert "session.sign_in" not in {
            event.get("metadata", {}).get("semantic_target")
            for event in map(json.loads, events.splitlines())
            if event.get("outcome") == "executed"
        }
    finally:
        service.close()


def test_synthetic_login_does_not_allow_cookie_free_access_or_echo_passwords() -> None:
    app = create_app(scenario=DemoScenario(mode="login_required"))
    client = app.test_client()
    protected = "/members/67890/accounts/savings"
    assert client.get(protected).status_code == 302
    invalid = client.post("/demo-login", data={"username": "demo-reviewer", "password": "canary"})
    assert b"canary" not in invalid.data
    assert client.get(protected).status_code == 302
    assert (
        client.post(
            "/demo-login", data={"username": "demo-reviewer", "password": "demo-only"}
        ).status_code
        == 302
    )
    assert client.get(protected).status_code == 200
    assert app.test_client().get(protected).status_code == 302
    assert client.post("/demo-login", data=b"x" * 5000).status_code == 413
