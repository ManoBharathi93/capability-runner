from __future__ import annotations

import time
from pathlib import Path

from demo_app.app import DemoScenario, create_app
from demo_app.fixtures import MEMBERS, ScenarioMode, get_member


def _client(mode: ScenarioMode = "normal", delay: float = 0.12):
    app = create_app(scenario=DemoScenario(mode=mode, search_delay_seconds=delay))
    app.config["TESTING"] = True
    return app.test_client()


def test_root_workspace_renders() -> None:
    client = _client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "iframe" in html
    assert "work-area" in html


def test_search_page_renders() -> None:
    client = _client()

    response = client.get("/members/search")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Member Search" in html
    assert "Member ID" in html


def test_valid_member_search_produces_correct_result() -> None:
    client = _client()

    response = client.post("/members/search", data={"member_id": "12345"})

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Avery Morgan" in html
    assert "12345" in html
    assert "Open" in html


def test_unknown_member_produces_not_found_state() -> None:
    client = _client()

    response = client.post("/members/search", data={"member_id": "00000"})

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No member found for the supplied Member ID." in html


def test_result_row_opens_correct_member() -> None:
    client = _client()

    response = client.post("/members/search", data={"member_id": "12345"})

    html = response.get_data(as_text=True)
    assert '/members/12345' in html


def test_member_details_contains_correct_identity() -> None:
    client = _client()

    response = client.get("/members/12345")

    html = response.get_data(as_text=True)
    assert "Member Details" in html
    assert "Avery Morgan" in html
    assert "Savings" in html
    assert "Checking" in html


def test_savings_account_navigation_returns_correct_page() -> None:
    client = _client()

    response = client.get("/members/12345/accounts/savings")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Savings Account" in html
    assert "12345" in html
    assert "$4,382.21" in html


def test_displayed_balance_matches_fixture_minor_units() -> None:
    client = _client()

    response = client.get("/members/12345/accounts/savings")

    html = response.get_data(as_text=True)
    assert "$4,382.21" in html
    member = get_member("12345")
    assert member is not None
    assert member.accounts[0].balance_minor_units == 438221


def test_restricted_member_shows_permission_denied() -> None:
    client = _client()

    response = client.get("/members/55555/accounts/savings")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "You do not have permission to view this account." in html


def test_risky_control_exists_but_does_not_mutate_fixture_data() -> None:
    client = _client()
    before = tuple(MEMBERS.items())

    response = client.post("/members/12345/danger/delete-member")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No changes have been made." in html
    assert tuple(MEMBERS.items()) == before


def test_normal_scenario_works_without_injected_delay_or_error() -> None:
    client = _client(mode="normal")

    response = client.post("/members/search", data={"member_id": "67890"})

    assert response.status_code == 200
    assert "Jordan Lee" in response.get_data(as_text=True)


def test_session_expired_displays_expected_state() -> None:
    client = _client(mode="session_expired")

    response = client.get("/members/search")

    html = response.get_data(as_text=True)
    assert "Your session has expired." in html


def test_slow_search_uses_configured_delay() -> None:
    client = _client(mode="slow_search", delay=0.05)

    started = time.perf_counter()
    response = client.post("/members/search", data={"member_id": "12345"})
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed >= 0.05


def test_html_contains_no_test_id_hooks() -> None:
    client = _client()

    for path in ["/", "/workspace", "/members/search", "/members/12345"]:
        html = client.get(path).get_data(as_text=True)
        assert "data-testid" not in html
        assert "test-id" not in html


def test_runner_source_does_not_import_demo_app() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src" / "capability_runner"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in source_root.rglob("*.py"))

    assert "demo_app" not in sources


def test_no_business_api_exists_for_balance_data() -> None:
    client = _client()

    assert client.get("/api/members/12345").status_code == 404
    assert client.get("/members/12345/balance.json").status_code == 404
