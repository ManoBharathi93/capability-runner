"""Direct Page input is a test stand-in, not physical human acceptance."""

import json
from collections import Counter
from pathlib import Path

import pytest

from capability_runner.application.operator_console import OperatorConsoleError
from capability_runner.contracts.operator_console import OperatorActionSubmission
from capability_runner.interaction.session_controller import SessionControllerError
from demo_app.product_http import ProductWorkflowService


@pytest.mark.parametrize(
    "action", ["savings", "unchanged", "wrong", "closed", "capture_missing", "privacy"]
)
def test_native_handoff_retains_browser_and_validates_outcome(
    tmp_path: Path,
    action: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def forbidden_model(*args: object, **kwargs: object) -> None:
        calls.append("unexpected")
        raise AssertionError("Handoff must not invoke a model")

    for module, client in [("openai", "OpenAI"), ("anthropic", "Anthropic"), ("gemma", "Gemma")]:
        monkeypatch.setattr(
            f"capability_runner.discovery.providers.{module}_client.{client}ModelClient.complete",
            forbidden_model,
        )
    success = action in {"savings", "capture_missing", "privacy"}
    service = ProductWorkflowService(
        output_root=tmp_path,
        environment_provider=lambda: {"CAPABILITY_RUNNER_BROWSER_HEADLESS": "true"},
    )
    try:
        started = service.start_intervention()
        identifier = str(started["intervention_id"])
        assert started["control_state"] == "pause_requested"
        assert started["generation"] == 1
        with pytest.raises(OperatorConsoleError, match="Take control"):
            service.return_control(identifier)
        live = service._get_live(identifier)  # pyright: ignore[reportPrivateUsage]
        execution = live.execution
        state = execution.adapter._sessions[execution.session.surface_session_id]
        page, context = state.page, state.context
        assert service.get_view(identifier)[1] == "image/png"
        granted = service.take_control(identifier)
        assert granted["control_state"] == "operator_controlled"
        assert granted["generation"] == 2
        assert granted["surface_session_id"] == started["surface_session_id"]

        async def direct_browser_input() -> None:
            for generation in [0, 2]:
                with pytest.raises(SessionControllerError):
                    async with execution.controller.automation_dispatch(
                        execution.record.control_session_id,
                        expected_generation=generation,
                    ):
                        pytest.fail("Automation was admitted during human ownership")
            if action == "capture_missing":
                await execution.adapter.stop_human_observation(execution.session)
            if action == "privacy":
                frame = page.frame(name="work-area")
                assert frame is not None
                await frame.evaluate("""() => {
                    const div = document.createElement('div');
                    div.innerHTML = '<input id="capture-text">'
                      + '<input id="capture-password" type="password">'
                      + '<input id="capture-otp" autocomplete="one-time-code">'
                      + '<select id="capture-select"><option>a</option><option>b</option></select>';
                    document.body.append(div);
                }""")
                for field in ["capture-text", "capture-password", "capture-otp"]:
                    await frame.locator(f"#{field}").fill("private-value-never-log")
                    await frame.locator(f"#{field}").press("Tab")
                await frame.locator("#capture-select").focus()
                await frame.locator("#capture-select").press("ArrowDown")
            if action == "closed":
                await page.close()
            elif success or action == "wrong":
                # Deliberately bypass both gateways: physical human equivalent.
                await (
                    page.frame_locator('iframe[name="work-area"]')
                    .get_by_role("row")
                    .filter(has_text="Savings" if success else "Checking")
                    .get_by_role("link", name="Open", exact=True)
                    .click()
                )
            assert state.page is page and state.context is context

        live.runner.run(direct_browser_input())
        with pytest.raises(OperatorConsoleError, match="managed browser"):
            service.execute_action(
                identifier,
                OperatorActionSubmission(
                    action_kind="click",
                    semantic_target="member.accounts.savings",
                ),
            )
        result = service.return_control(identifier)
        assert result["status"] == (
            "SUCCESS" if success else ("FAILURE" if action == "closed" else "VALIDATION_FAILED")
        )
        assert result["replay_model_calls"] == 0
        assert calls == []
        assert execution.automation_counter.executed == Counter(
            {
                "member.search.member_id": 1,
                "member.search.submit": 1,
                "member.results.open": 1,
            }
        )
        assert execution.operator_counter.executed == Counter()
        assert service.list_active_interventions() == []
        with pytest.raises(OperatorConsoleError, match="not active"):
            service.return_control(identifier)
        assert state.page is page and state.context is context
        raw_evidence = live.recorder.path.read_text()
        assert "private-value-never-log" not in raw_evidence
        events = [json.loads(line) for line in raw_evidence.splitlines()]
        codes = [event.get("reason_code") for event in events]
        assert "AUTOMATION_QUIESCED" in codes
        assert "HUMAN_CONTROL_GRANTED" in codes
        assert "HUMAN_CONTROL_RETURNED" in codes
        observations = [e for e in events if e.get("reason_code") == "HUMAN_BROWSER_ACTION"]
        for event in observations:
            assert event["metadata"]["source"] == "direct_browser_interaction"
            assert event["metadata"]["actor"] == "human"
            assert event["outcome"] == "observed"
            assert "value" not in event["metadata"]
        if success:
            assert result["identity_before"] == result["identity_after"]
            assert result["generation_after"] == 3
            assert result["outputs"] == {"balance_minor_units": 98765, "currency": "USD"}
            assert (
                action == "capture_missing"
                or len([e for e in observations if e["metadata"]["action_type"] == "click"]) >= 1
            )
            assert "AUTOMATION_CONTROL_RESTORED" in codes
        else:
            assert result["outputs"] == {}
            assert "AUTOMATION_CONTROL_RESTORED" not in codes
        if action == "savings":
            assert len([e for e in observations if e["metadata"]["action_type"] == "click"]) == 1
        if action == "capture_missing":
            assert observations == []
        if action == "privacy":
            changes = [e for e in observations if e["metadata"]["action_type"] == "change"]
            assert len(changes) == 2  # Ordinary field and select; password/OTP excluded.
            assert all(e["metadata"]["value_redacted"] for e in changes)
    finally:
        service.close()
