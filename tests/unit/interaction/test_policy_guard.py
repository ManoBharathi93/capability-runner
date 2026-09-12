from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import HttpUrl, SecretStr, TypeAdapter

from capability_runner.contracts.actions import ClickAction, FillAction, NavigateAction, WaitAction
from capability_runner.contracts.policy import (
    AllowedDestination,
    ClickPolicyRule,
    FillPolicyRule,
    NavigatePolicyRule,
    PolicyContext,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.surfaces import SemanticTargetRef
from capability_runner.contracts.targets import ProfileTarget
from capability_runner.interaction.policy_guard import PolicyGuard


def _build_policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="policy-core",
        version="1.0",
        allowed_contexts=(TrustedApplicationProfile(application="bank", profile="core"),),
        rules=(
            ClickPolicyRule(
                rule_id="click-allowed",
                effect="ALLOW",
                semantic_target=SemanticTargetRef(value="member.search.submit"),
            ),
            FillPolicyRule(
                rule_id="fill-denied",
                effect="DENY",
                semantic_target=SemanticTargetRef(value="member.search.member_id"),
            ),
            NavigatePolicyRule(
                rule_id="navigate-approval",
                effect="REQUIRE_APPROVAL",
                destination=AllowedDestination(
                    scheme="https",
                    hostname="trusted.example",
                    port=443,
                    path="/member",
                ),
            ),
            NavigatePolicyRule(
                rule_id="navigate-denied",
                effect="DENY",
                destination=AllowedDestination(
                    scheme="https",
                    hostname="trusted.example",
                    port=443,
                    path="/blocked",
                ),
            ),
        ),
    )


def _context() -> PolicyContext:
    return PolicyContext(application="bank", profile="core")


def _semantic(value: str) -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def test_permitted_safe_action_allows(tmp_path: Path) -> None:
    guard = PolicyGuard(_build_policy())
    action = ClickAction(
        target=ProfileTarget(kind="profile", application="bank", profile="core"),
    )

    decision = guard.evaluate(action, _context(), _semantic("member.search.submit"))

    assert decision.decision == "ALLOW"
    assert decision.reason_code == "ALLOWED_BY_RULE"
    assert decision.rule_id == "click-allowed"


def test_prohibited_action_denies() -> None:
    guard = PolicyGuard(_build_policy())
    action = FillAction(
        target=ProfileTarget(kind="profile", application="bank", profile="core-danger"),
        value=SecretStr("alice"),
    )

    decision = guard.evaluate(action, _context(), _semantic("member.search.member_id"))

    assert decision.decision == "DENY"
    assert decision.reason_code == "ACTION_NOT_ALLOWED"
    assert decision.rule_id == "fill-denied"


def test_risky_configured_action_requires_approval() -> None:
    guard = PolicyGuard(_build_policy())
    action = NavigateAction(
        url=TypeAdapter(HttpUrl).validate_python("https://trusted.example/member")
    )

    decision = guard.evaluate(action, _context())

    assert decision.decision == "REQUIRE_APPROVAL"
    assert decision.reason_code == "APPROVAL_REQUIRED"
    assert decision.rule_id == "navigate-approval"


def test_unknown_action_denies() -> None:
    guard = PolicyGuard(_build_policy())
    action = WaitAction(seconds=1.0)

    decision = guard.evaluate(action, _context())

    assert decision.decision == "DENY"
    assert decision.reason_code == "ACTION_NOT_ALLOWED"


def test_unknown_application_profile_denies() -> None:
    guard = PolicyGuard(_build_policy())
    action = ClickAction(
        target=ProfileTarget(kind="profile", application="bank", profile="core"),
    )

    decision = guard.evaluate(
        action,
        PolicyContext(application="other", profile="core"),
        _semantic("member.search.submit"),
    )

    assert decision.decision == "DENY"
    assert decision.reason_code == "UNKNOWN_APPLICATION"


def test_unauthorized_target_denies() -> None:
    guard = PolicyGuard(_build_policy())
    action = ClickAction(
        target=ProfileTarget(kind="profile", application="bank", profile="not-allowed"),
    )

    decision = guard.evaluate(action, _context(), _semantic("member.unknown.control"))

    assert decision.decision == "DENY"
    assert decision.reason_code == "TARGET_NOT_ALLOWED"


def test_approved_navigation_allows_allowed_origin_and_path() -> None:
    policy = PolicyDefinition(
        policy_id="policy-nav",
        version="1.0",
        allowed_contexts=(TrustedApplicationProfile(application="bank", profile="core"),),
        rules=(
            NavigatePolicyRule(
                rule_id="nav-allow",
                effect="ALLOW",
                destination=AllowedDestination(
                    scheme="https",
                    hostname="trusted.example",
                    port=443,
                    path="/member",
                ),
            ),
        ),
    )
    guard = PolicyGuard(policy)

    decision = guard.evaluate(
        NavigateAction(url=TypeAdapter(HttpUrl).validate_python("https://trusted.example/member")),
        _context(),
    )

    assert decision.decision == "ALLOW"
    assert decision.reason_code == "ALLOWED_BY_RULE"


@pytest.mark.parametrize(
    ("url", "reason_code"),
    [
        ("https://trusted.example.evil.example/member", "DESTINATION_NOT_ALLOWED"),
        ("http://trusted.example/member", "DESTINATION_NOT_ALLOWED"),
        ("https://trusted.example:444/member", "DESTINATION_NOT_ALLOWED"),
        ("https://trusted.example@evil.example/member", "DESTINATION_NOT_ALLOWED"),
        ("https://trusted.example/member-admin", "DESTINATION_NOT_ALLOWED"),
    ],
)
def test_navigation_rejects_confusing_or_unsupported_urls(url: str, reason_code: str) -> None:
    policy = PolicyDefinition(
        policy_id="policy-nav",
        version="1.0",
        allowed_contexts=(TrustedApplicationProfile(application="bank", profile="core"),),
        rules=(
            NavigatePolicyRule(
                rule_id="nav-allow",
                effect="ALLOW",
                destination=AllowedDestination(
                    scheme="https",
                    hostname="trusted.example",
                    port=443,
                    path="/member",
                ),
            ),
        ),
    )
    guard = PolicyGuard(policy)

    decision = guard.evaluate(
        NavigateAction(url=TypeAdapter(HttpUrl).validate_python(url)),
        _context(),
    )

    assert decision.decision == "DENY"
    assert decision.reason_code == reason_code


def test_navigation_rejects_unsupported_scheme() -> None:
    policy = PolicyDefinition(
        policy_id="policy-nav",
        version="1.0",
        allowed_contexts=(TrustedApplicationProfile(application="bank", profile="core"),),
        rules=(
            NavigatePolicyRule(
                rule_id="nav-allow",
                effect="ALLOW",
                destination=AllowedDestination(
                    scheme="https",
                    hostname="trusted.example",
                    port=443,
                    path="/member",
                ),
            ),
        ),
    )
    guard = PolicyGuard(policy)

    decision = guard.evaluate(NavigateAction.model_construct(url="javascript:alert(1)"), _context())

    assert decision.decision == "DENY"
    assert decision.reason_code == "DESTINATION_NOT_ALLOWED"


def test_boundary_paths_are_exact_not_prefix_based() -> None:
    policy = PolicyDefinition(
        policy_id="policy-nav",
        version="1.0",
        allowed_contexts=(TrustedApplicationProfile(application="bank", profile="core"),),
        rules=(
            NavigatePolicyRule(
                rule_id="nav-allow",
                effect="ALLOW",
                destination=AllowedDestination(
                    scheme="https",
                    hostname="trusted.example",
                    port=443,
                    path="/member",
                ),
            ),
        ),
    )
    guard = PolicyGuard(policy)

    decision = guard.evaluate(
        NavigateAction(
            url=TypeAdapter(HttpUrl).validate_python("https://trusted.example/member-admin")
        ),
        _context(),
    )

    assert decision.decision == "DENY"
    assert decision.reason_code == "DESTINATION_NOT_ALLOWED"


def test_untrusted_metadata_cannot_override_policy() -> None:
    guard = PolicyGuard(_build_policy())
    action = FillAction(
        target=ProfileTarget(kind="profile", application="bank", profile="core-danger"),
        value=SecretStr("alice"),
    )

    decision = guard.evaluate(action, _context(), _semantic("member.search.member_id"))

    assert decision.decision == "DENY"
    assert decision.reason_code == "ACTION_NOT_ALLOWED"


def test_require_approval_is_distinct_from_allow() -> None:
    guard = PolicyGuard(_build_policy())
    allow_decision = guard.evaluate(
        ClickAction(target=ProfileTarget(kind="profile", application="bank", profile="core")),
        _context(),
        _semantic("member.search.submit"),
    )
    approval_decision = guard.evaluate(
        NavigateAction(url=TypeAdapter(HttpUrl).validate_python("https://trusted.example/member")),
        _context(),
    )

    assert allow_decision.decision == "ALLOW"
    assert approval_decision.decision == "REQUIRE_APPROVAL"
    assert allow_decision.decision != approval_decision.decision


def test_duplicate_rules_are_rejected() -> None:
    with pytest.raises(ValueError):
        PolicyDefinition(
            policy_id="policy-dup",
            version="1.0",
            allowed_contexts=(TrustedApplicationProfile(application="bank", profile="core"),),
            rules=(
                ClickPolicyRule(
                    rule_id="dup-1",
                    effect="ALLOW",
                    semantic_target=_semantic("member.search.submit"),
                ),
                ClickPolicyRule(
                    rule_id="dup-2",
                    effect="DENY",
                    semantic_target=_semantic("member.search.submit"),
                ),
            ),
        )


def test_policy_evaluation_does_not_mutate_inputs() -> None:
    policy = _build_policy()
    action = ClickAction(target=ProfileTarget(kind="profile", application="bank", profile="core"))
    before_policy = policy.model_dump(mode="python")
    before_action = action.model_dump(mode="python")

    guard = PolicyGuard(policy)
    guard.evaluate(action, _context(), _semantic("member.search.submit"))

    assert policy.model_dump(mode="python") == before_policy
    assert action.model_dump(mode="python") == before_action


def test_importing_policy_modules_has_no_side_effects(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import capability_runner.contracts.policy, capability_runner.interaction.policy_guard",
        ],
        check=True,
        cwd=tmp_path,
    )
    assert list(tmp_path.iterdir()) == []
