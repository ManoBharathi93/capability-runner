"""Synthetic sign-in composition; never a production authentication boundary."""

from capability_runner.application.demo_configuration import (
    build_core_bank_demo_profile,
    build_demo_automation_policy,
    build_demo_capability,
    semantic_target,
)
from capability_runner.capabilities.capability_validator import CapabilityValidator
from capability_runner.contracts.capabilities import CapabilityDefinition
from capability_runner.contracts.policy import ClickPolicyRule
from capability_runner.contracts.surfaces import BrowserTargetBinding, CssLocator, FrameContext

DEMO_LOGIN_USER = "demo-reviewer"
DEMO_LOGIN_PASSWORD = "demo-only"
LOGIN_CAPABILITY_ID = "lookup_savings_after_sign_in"


def build_login_handoff(base_url: str):
    profile = build_core_bank_demo_profile(f"{base_url}/")
    bindings = tuple(
        BrowserTargetBinding(
            semantic_target=semantic_target(target),
            frame=FrameContext(name="work-area"),
            locator_candidates=(CssLocator(selector=selector),),
        )
        for target, selector in (
            ("session.sign_in", "button[data-demo-sign-in]"),
            ("session.signed_in", "[data-session-state]"),
        )
    )
    profile = profile.model_copy(update={"target_bindings": (*profile.target_bindings, *bindings)})
    policy = build_demo_automation_policy(require_savings_approval=False)
    policy = policy.model_copy(
        update={
            "rules": (
                *policy.rules,
                ClickPolicyRule(
                    rule_id="human-sign-in",
                    effect="REQUIRE_APPROVAL",
                    semantic_target=semantic_target("session.sign_in"),
                ),
            )
        }
    )
    definition = build_demo_capability().definition.model_dump(mode="json")
    definition["capability_id"] = LOGIN_CAPABILITY_ID
    definition["name"] = "Sign in, then look up savings"
    definition["steps"].insert(
        0,
        {
            "kind": "action",
            "step_id": "human_sign_in",
            "action": {"kind": "click", "target": {"value": "session.sign_in"}},
            "postcondition": {
                "kind": "target_text_equals",
                "target": {"value": "session.signed_in"},
                "expected": {"kind": "literal", "value": "Signed in as demo-reviewer"},
            },
        },
    )
    capability = CapabilityValidator().validate(CapabilityDefinition.model_validate(definition))
    return profile, policy, capability
