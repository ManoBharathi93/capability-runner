"""Flask application factory for the synthetic legacy banking target."""

from __future__ import annotations

import time
from dataclasses import dataclass

from flask import Flask, abort, render_template, request, url_for

from .fixtures import AccountFixture, ScenarioMode, get_member


@dataclass(frozen=True, slots=True)
class DemoScenario:
    mode: ScenarioMode = "normal"
    search_delay_seconds: float = 0.12


def create_app(*, scenario: DemoScenario | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DEMO_SCENARIO"] = scenario or DemoScenario()

    @app.get("/")
    def root() -> str:
        return render_template("shell.html", workspace_url=url_for("workspace"))

    @app.get("/workspace")
    def workspace() -> str:
        if _scenario(app).mode == "session_expired":
            return render_template("session_expired.html")
        return render_template(
            "workspace.html",
            search_url=url_for("search_members"),
            scenario_label=_scenario(app).mode.replace("_", " ").title(),
        )

    @app.route("/members/search", methods=["GET", "POST"])
    def search_members() -> str:
        if _scenario(app).mode == "session_expired":
            return render_template("session_expired.html")

        if request.method == "GET":
            return render_template("search_form.html", search_url=url_for("search_members"))

        member_id = request.form.get("member_id", "").strip()
        if _scenario(app).mode == "slow_search":
            time.sleep(_scenario(app).search_delay_seconds)

        member = get_member(member_id)
        if member is None:
            return render_template("member_not_found.html", member_id=member_id)

        return render_template(
            "search_results.html",
            member=member,
            member_details_url=url_for("member_details", member_id=member.member_id),
        )

    @app.get("/members/<member_id>")
    def member_details(member_id: str) -> str:
        if _scenario(app).mode == "session_expired":
            return render_template("session_expired.html")

        member = get_member(member_id)
        if member is None:
            return render_template("member_not_found.html", member_id=member_id)

        return render_template(
            "member_details.html",
            member=member,
            savings_url=url_for("account_savings", member_id=member.member_id),
            checking_url=url_for("account_checking", member_id=member.member_id),
            risky_action_url=url_for("delete_member_simulation", member_id=member.member_id),
        )

    @app.get("/members/<member_id>/accounts/savings")
    def account_savings(member_id: str) -> str:
        if _scenario(app).mode == "session_expired":
            return render_template("session_expired.html")

        member = get_member(member_id)
        if member is None:
            return render_template("member_not_found.html", member_id=member_id)

        account = member.get_account("savings")
        if account is None:
            abort(404)
        if member.status == "Restricted":
            return render_template("permission_denied.html", member=member, account=account)

        return render_template(
            "account_savings.html",
            member=member,
            account=account,
            formatted_balance=_format_balance(account),
        )

    @app.get("/members/<member_id>/accounts/checking")
    def account_checking(member_id: str) -> str:
        if _scenario(app).mode == "session_expired":
            return render_template("session_expired.html")

        member = get_member(member_id)
        if member is None:
            return render_template("member_not_found.html", member_id=member_id)

        account = member.get_account("checking")
        if account is None:
            abort(404)

        return render_template(
            "account_checking.html",
            member=member,
            account=account,
            formatted_balance=_format_balance(account),
        )

    @app.post("/members/<member_id>/danger/delete-member")
    def delete_member_simulation(member_id: str) -> str:
        if _scenario(app).mode == "session_expired":
            return render_template("session_expired.html")

        member = get_member(member_id)
        if member is None:
            return render_template("member_not_found.html", member_id=member_id)

        return render_template("destructive_simulation.html", member=member)

    return app


def _scenario(app: Flask) -> DemoScenario:
    return app.config["DEMO_SCENARIO"]


def _format_balance(account: AccountFixture) -> str:
    whole_units, fractional_units = divmod(account.balance_minor_units, 100)
    formatted = f"{whole_units:,}.{fractional_units:02d}"
    return f"${formatted}"
