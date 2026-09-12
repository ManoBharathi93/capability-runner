from __future__ import annotations

import json
from typing import cast

import pytest
from pydantic import HttpUrl, SecretStr, TypeAdapter, ValidationError

from capability_runner.contracts.actions import (
    ActionApplied,
    ActionFailed,
    ActionRejected,
    ActionResult,
    ActionSpec,
    ClickAction,
    FillAction,
    NavigateAction,
    WaitAction,
)
from capability_runner.contracts.observations import (
    DialogObservation,
    ObservationSpec,
    OutcomeObservation,
    PageObservation,
)
from capability_runner.contracts.requests import (
    DiscoveryRequest,
    PublicParameter,
    ReplayRequest,
    RequestParameter,
    SensitiveParameter,
)
from capability_runner.contracts.runs import (
    RunBusinessOutcome,
    RunFailure,
    RunResult,
    RunState,
    RunSuccess,
)
from capability_runner.contracts.sessions import (
    AutomationOwner,
    OperatorOwner,
    SessionOwner,
    SessionState,
)
from capability_runner.contracts.targets import (
    ProfileTarget,
    TargetSpec,
    UrlTarget,
)


def test_target_variants_round_trip() -> None:
    example_url: HttpUrl = TypeAdapter(HttpUrl).validate_python("https://example.com")
    example_app_url: HttpUrl = TypeAdapter(HttpUrl).validate_python("https://example.com/app")
    url_target = UrlTarget(kind="url", url=example_url, label="portal")
    profile_target = ProfileTarget(
        kind="profile",
        application="core-banking",
        profile="demo",
        entry_url=example_app_url,
    )

    assert isinstance(url_target, UrlTarget)
    assert isinstance(profile_target, ProfileTarget)
    assert TypeAdapter(TargetSpec).validate_json(url_target.model_dump_json()) == url_target
    assert TypeAdapter(TargetSpec).validate_json(profile_target.model_dump_json()) == profile_target


def test_target_variants_from_raw_json() -> None:
    url_target_json = json.dumps({"kind": "url", "url": "https://example.com", "label": "portal"})
    profile_target_json = json.dumps(
        {
            "kind": "profile",
            "application": "core-banking",
            "profile": "demo",
            "entry_url": "https://example.com/app",
        }
    )

    assert TypeAdapter(TargetSpec).validate_json(url_target_json) == UrlTarget(
        kind="url",
        url=TypeAdapter(HttpUrl).validate_python("https://example.com"),
        label="portal",
    )
    assert TypeAdapter(TargetSpec).validate_json(profile_target_json) == ProfileTarget(
        kind="profile",
        application="core-banking",
        profile="demo",
        entry_url=TypeAdapter(HttpUrl).validate_python("https://example.com/app"),
    )


def test_target_unknown_variant_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(TargetSpec).validate_json(json.dumps({"kind": "desktop", "application": "x"}))

    assert "desktop" in str(exc_info.value)


def test_target_missing_variant_information_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(TargetSpec).validate_json(json.dumps({"application": "x"}))

    assert exc_info.value


def test_public_and_sensitive_request_parameter_variants() -> None:
    public_parameter = PublicParameter(kind="public", name="member_id", value="12345")
    sensitive_parameter = SensitiveParameter(
        kind="sensitive", name="session_token", value=SecretStr("s3cr3t")
    )

    assert isinstance(public_parameter, PublicParameter)
    assert isinstance(sensitive_parameter, SensitiveParameter)
    public_round_trip = cast(
        PublicParameter,
        TypeAdapter(RequestParameter).validate_json(public_parameter.model_dump_json()),
    )
    assert public_round_trip == public_parameter
    assert "s3cr3t" not in sensitive_parameter.model_dump_json()
    assert "s3cr3t" not in repr(sensitive_parameter)
    assert sensitive_parameter.value.get_secret_value() == "s3cr3t"
    sensitive_round_trip = cast(
        SensitiveParameter,
        TypeAdapter(RequestParameter).validate_json(sensitive_parameter.model_dump_json()),
    )
    assert sensitive_round_trip.value.get_secret_value() == "**********"
    assert json.loads(sensitive_parameter.model_dump_json())["value"] == "**********"


def test_request_parameter_variants_from_raw_json() -> None:
    public_json = json.dumps({"kind": "public", "name": "member_id", "value": "12345"})
    sensitive_json = json.dumps(
        {"kind": "sensitive", "name": "session_token", "value": "s3cr3t"}
    )

    public_parameter = cast(
        PublicParameter,
        TypeAdapter(RequestParameter).validate_json(public_json),
    )
    sensitive_parameter = cast(
        SensitiveParameter,
        TypeAdapter(RequestParameter).validate_json(sensitive_json),
    )

    assert public_parameter == PublicParameter(kind="public", name="member_id", value="12345")
    assert isinstance(sensitive_parameter, SensitiveParameter)
    assert sensitive_parameter.value.get_secret_value() == "s3cr3t"
    assert "s3cr3t" not in repr(sensitive_parameter)
    assert "s3cr3t" not in sensitive_parameter.model_dump_json()


def test_request_parameter_unknown_variant_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(RequestParameter).validate_json(
            json.dumps({"kind": "private", "name": "session_token", "value": "x"})
        )

    assert "private" in str(exc_info.value)


def test_request_parameter_missing_variant_information_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(RequestParameter).validate_json(json.dumps({"name": "session_token"}))

    assert exc_info.value


def test_requests_round_trip_and_required_fields() -> None:
    discovery = DiscoveryRequest(
        goal="Look up the account",
        target=ProfileTarget(kind="profile", application="core-banking", profile="demo"),
        parameters=[PublicParameter(kind="public", name="member_id", value="12345")],
    )
    replay = ReplayRequest(
        capability_id="cap-member-balance-v1",
        target=UrlTarget(
            kind="url", url=TypeAdapter(HttpUrl).validate_python("https://example.com")
        ),
        parameters=discovery.parameters,
        strict=True,
    )

    assert DiscoveryRequest.model_fields["goal"].is_required()
    assert ReplayRequest.model_fields["strict"].default is True
    assert TypeAdapter(DiscoveryRequest).validate_json(discovery.model_dump_json()) == discovery
    assert TypeAdapter(ReplayRequest).validate_json(replay.model_dump_json()) == replay


def test_requests_accept_raw_json_targets_and_parameters() -> None:
    discovery_json = json.dumps(
        {
            "goal": "Look up the account",
            "target": {
                "kind": "profile",
                "application": "core-banking",
                "profile": "demo",
            },
            "parameters": [
                {"kind": "public", "name": "member_id", "value": "12345"},
                {"kind": "sensitive", "name": "session_token", "value": "s3cr3t"},
            ],
        }
    )

    parsed = TypeAdapter(DiscoveryRequest).validate_json(discovery_json)
    assert parsed.target == ProfileTarget(
        kind="profile", application="core-banking", profile="demo"
    )
    assert parsed.parameters[0] == PublicParameter(kind="public", name="member_id", value="12345")
    assert isinstance(parsed.parameters[1], SensitiveParameter)
    assert parsed.parameters[1].value.get_secret_value() == "s3cr3t"
    assert "s3cr3t" not in parsed.model_dump_json()


def test_requests_reject_missing_required_and_unknown_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        DiscoveryRequest.model_validate(
            {
                "target": {"kind": "profile", "application": "x", "profile": "demo"},
                "extra": True,
            }
        )

    message = str(exc_info.value)
    assert "goal" in message
    assert "extra" in message


def test_action_variants_round_trip_and_sensitive_value_behavior() -> None:
    example_url: HttpUrl = TypeAdapter(HttpUrl).validate_python("https://example.com")
    next_url: HttpUrl = TypeAdapter(HttpUrl).validate_python("https://example.com/next")
    click_action = ClickAction(
        kind="click",
        target=UrlTarget(kind="url", url=example_url, label="go"),
        button="left",
    )
    wait_action = WaitAction(kind="wait", seconds=2.5)
    navigate_action = NavigateAction(kind="navigate", url=next_url)
    fill_sensitive = FillAction(
        kind="fill",
        target=ProfileTarget(kind="profile", application="core-banking", profile="demo"),
        value=SecretStr("secret-input"),
    )

    assert isinstance(click_action, ClickAction)
    click_round_trip = cast(
        ClickAction,
        TypeAdapter(ActionSpec).validate_json(click_action.model_dump_json()),
    )
    wait_round_trip = cast(
        WaitAction,
        TypeAdapter(ActionSpec).validate_json(wait_action.model_dump_json()),
    )
    navigate_round_trip = cast(
        NavigateAction,
        TypeAdapter(ActionSpec).validate_json(navigate_action.model_dump_json()),
    )

    assert click_round_trip == click_action
    assert wait_round_trip == wait_action
    assert navigate_round_trip == navigate_action

    redacted_fill = cast(
        FillAction,
        TypeAdapter(ActionSpec).validate_json(fill_sensitive.model_dump_json()),
    )
    assert redacted_fill.value.get_secret_value() == "**********"
    assert "secret-input" not in repr(fill_sensitive)
    assert "secret-input" not in fill_sensitive.model_dump_json()
    assert fill_sensitive.value.get_secret_value() == "secret-input"
    assert json.loads(fill_sensitive.model_dump_json())["value"] == "**********"


def test_action_variants_from_raw_json() -> None:
    click_json = json.dumps(
        {
            "kind": "click",
            "target": {"kind": "url", "url": "https://example.com", "label": "go"},
            "button": "left",
        }
    )
    wait_json = json.dumps({"kind": "wait", "seconds": 2.5})
    navigate_json = json.dumps({"kind": "navigate", "url": "https://example.com/next"})

    assert TypeAdapter(ActionSpec).validate_json(click_json) == ClickAction(
        kind="click",
        target=UrlTarget(
            kind="url",
            url=TypeAdapter(HttpUrl).validate_python("https://example.com"),
            label="go",
        ),
        button="left",
    )
    assert TypeAdapter(ActionSpec).validate_json(wait_json) == WaitAction(
        kind="wait", seconds=2.5
    )
    assert TypeAdapter(ActionSpec).validate_json(navigate_json) == NavigateAction(
        kind="navigate",
        url=TypeAdapter(HttpUrl).validate_python("https://example.com/next"),
    )


def test_action_unknown_variant_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(ActionSpec).validate_json(json.dumps({"kind": "drag"}))

    assert "drag" in str(exc_info.value)


def test_action_missing_variant_information_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(ActionSpec).validate_json(
            json.dumps({"target": {"kind": "url", "url": "https://example.com"}})
        )

    assert exc_info.value


def test_action_results_and_observations_round_trip() -> None:
    example_url: HttpUrl = TypeAdapter(HttpUrl).validate_python("https://example.com")
    summary_url: HttpUrl = TypeAdapter(HttpUrl).validate_python("https://example.com/summary")
    observation = PageObservation(
        kind="page",
        url=example_url,
        title="Portal",
        visible_text="Member summary",
    )
    operational_observation = PageObservation(
        kind="page",
        url=summary_url,
        title="Portal",
        visible_text="Member summary",
        operational_values=(SecretStr("token-1"), SecretStr("token-2")),
    )
    dialog = DialogObservation(kind="dialog", dialog_type="confirm", message="Continue?")
    outcome = OutcomeObservation(
        kind="outcome", outcome="business_outcome", summary="No such member"
    )
    applied = ActionApplied(
        action=ClickAction(
            kind="click",
            target=UrlTarget(kind="url", url=example_url, label="go"),
        ),
        observation=dialog,
    )
    rejected = ActionRejected(kind="rejected", reason="policy", message="Blocked by allowlist")
    failed = ActionFailed(kind="failed", message="Timed out")

    assert isinstance(observation, PageObservation)
    assert TypeAdapter(ObservationSpec).validate_json(observation.model_dump_json()) == observation
    assert TypeAdapter(ObservationSpec).validate_json(dialog.model_dump_json()) == dialog
    assert TypeAdapter(ObservationSpec).validate_json(outcome.model_dump_json()) == outcome
    assert "token-1" not in operational_observation.model_dump_json()
    assert "token-1" not in repr(operational_observation)
    assert operational_observation.operational_values[0].get_secret_value() == "token-1"

    operational_round_trip = cast(
        PageObservation,
        TypeAdapter(ObservationSpec).validate_json(operational_observation.model_dump_json()),
    )
    assert operational_round_trip.operational_values[0].get_secret_value() == "**********"
    assert TypeAdapter(ActionResult).validate_json(applied.model_dump_json()) == applied
    assert TypeAdapter(ActionResult).validate_json(rejected.model_dump_json()) == rejected
    assert TypeAdapter(ActionResult).validate_json(failed.model_dump_json()) == failed
    assert "token-1" not in observation.model_dump_json()
    assert "token-1" not in repr(observation)


def test_observations_from_raw_json() -> None:
    page_json = json.dumps(
        {
            "kind": "page",
            "url": "https://example.com",
            "title": "Portal",
            "visible_text": "Member summary",
        }
    )
    dialog_json = json.dumps(
        {"kind": "dialog", "dialog_type": "confirm", "message": "Continue?"}
    )
    outcome_json = json.dumps(
        {"kind": "outcome", "outcome": "business_outcome", "summary": "No such member"}
    )

    assert TypeAdapter(ObservationSpec).validate_json(page_json) == PageObservation(
        kind="page",
        url=TypeAdapter(HttpUrl).validate_python("https://example.com"),
        title="Portal",
        visible_text="Member summary",
    )
    assert TypeAdapter(ObservationSpec).validate_json(dialog_json) == DialogObservation(
        kind="dialog", dialog_type="confirm", message="Continue?"
    )
    assert TypeAdapter(ObservationSpec).validate_json(outcome_json) == OutcomeObservation(
        kind="outcome", outcome="business_outcome", summary="No such member"
    )


def test_observation_unknown_variant_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(ObservationSpec).validate_json(
            json.dumps({"kind": "toast", "message": "x"})
        )

    assert "toast" in str(exc_info.value)


def test_observation_missing_variant_information_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(ObservationSpec).validate_json(json.dumps({"visible_text": "x"}))

    assert exc_info.value


def test_session_and_run_models_round_trip() -> None:
    owner = AutomationOwner(kind="automation", run_id="run-1")
    operator_owner = OperatorOwner(kind="operator", operator_id="op-1", display_name="Alex")
    session = SessionState(
        session_id="session-1",
        control_state="automation_controlled",
        owner=owner,
        control_generation=7,
    )
    state = RunState(run_id="run-1", phase="running", current_step="click-member")
    success = RunSuccess(kind="success", run_id="run-1", outputs={"balance": "$100"})
    business_outcome = RunBusinessOutcome(
        kind="business_outcome", run_id="run-2", outcome="no such member"
    )
    failure = RunFailure(
        kind="failure", run_id="run-3", expected="record detail", observed="timeout"
    )

    owner_round_trip = cast(
        AutomationOwner,
        TypeAdapter(SessionOwner).validate_json(owner.model_dump_json()),
    )
    operator_round_trip = cast(
        OperatorOwner,
        TypeAdapter(SessionOwner).validate_json(operator_owner.model_dump_json()),
    )
    session_round_trip = TypeAdapter(SessionState).validate_json(session.model_dump_json())
    state_round_trip = TypeAdapter(RunState).validate_json(state.model_dump_json())
    success_round_trip = cast(
        RunSuccess,
        TypeAdapter(RunResult).validate_json(success.model_dump_json()),
    )
    business_round_trip = cast(
        RunBusinessOutcome,
        TypeAdapter(RunResult).validate_json(business_outcome.model_dump_json()),
    )
    failure_round_trip = cast(
        RunFailure,
        TypeAdapter(RunResult).validate_json(failure.model_dump_json()),
    )

    assert owner_round_trip == owner
    assert operator_round_trip == operator_owner
    assert session_round_trip == session
    assert state_round_trip == state
    assert success_round_trip == success
    assert business_round_trip == business_outcome
    assert failure_round_trip == failure


def test_session_owner_and_run_result_from_raw_json() -> None:
    automation_json = json.dumps({"kind": "automation", "run_id": "run-1"})
    operator_json = json.dumps(
        {"kind": "operator", "operator_id": "op-1", "display_name": "Alex"}
    )
    success_json = json.dumps(
        {"kind": "success", "run_id": "run-1", "outputs": {"balance": "$100"}}
    )
    business_json = json.dumps(
        {"kind": "business_outcome", "run_id": "run-2", "outcome": "no such member"}
    )
    failure_json = json.dumps(
        {
            "kind": "failure",
            "run_id": "run-3",
            "expected": "record detail",
            "observed": "timeout",
        }
    )

    assert TypeAdapter(SessionOwner).validate_json(automation_json) == AutomationOwner(
        kind="automation", run_id="run-1"
    )
    assert TypeAdapter(SessionOwner).validate_json(operator_json) == OperatorOwner(
        kind="operator", operator_id="op-1", display_name="Alex"
    )
    assert TypeAdapter(RunResult).validate_json(success_json) == RunSuccess(
        kind="success", run_id="run-1", outputs={"balance": "$100"}
    )
    assert TypeAdapter(RunResult).validate_json(business_json) == RunBusinessOutcome(
        kind="business_outcome", run_id="run-2", outcome="no such member"
    )
    assert TypeAdapter(RunResult).validate_json(failure_json) == RunFailure(
        kind="failure", run_id="run-3", expected="record detail", observed="timeout"
    )


def test_session_owner_and_run_result_unknown_variants_are_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(SessionOwner).validate_json(
            json.dumps({"kind": "human", "operator_id": "op-1"})
        )

    assert "human" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(RunResult).validate_json(
            json.dumps({"kind": "unknown", "run_id": "run-1"})
        )

    assert "unknown" in str(exc_info.value)


def test_session_owner_and_run_result_missing_variant_information_are_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(SessionOwner).validate_json(json.dumps({"run_id": "run-1"}))

    assert exc_info.value

    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(RunResult).validate_json(json.dumps({"run_id": "run-1", "expected": "x"}))

    assert exc_info.value
