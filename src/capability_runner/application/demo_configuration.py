"""Trusted CoreBank configuration for reviewer demo composition."""

from __future__ import annotations

from capability_runner.capabilities.capability_validator import (
    CapabilityValidator,
    ValidatedCapability,
)
from capability_runner.contracts.capabilities import CapabilityDefinition
from capability_runner.contracts.capability_building import (
    CapabilityBuildRequest,
    InputEqualitySuccessTemplate,
    LiteralEqualitySuccessTemplate,
    VisibleSuccessTemplate,
)
from capability_runner.contracts.discovery import DiscoveryResult
from capability_runner.contracts.policy import (
    ClickPolicyRule,
    FillPolicyRule,
    PolicyDefinition,
    TrustedApplicationProfile,
)
from capability_runner.contracts.surfaces import (
    ApplicationProfile,
    BrowserTargetBinding,
    CssLocator,
    FrameContext,
    InputValueRef,
    LabelLocator,
    LiteralValue,
    RoleLocator,
    RowMatch,
    RowScope,
    SemanticTargetRef,
    TextLocator,
)

DEMO_CAPABILITY_ID = "lookup_savings_balance"
DEMO_CAPABILITY_VERSION = "1.0.0"


def semantic_target(value: str) -> SemanticTargetRef:
    return SemanticTargetRef(value=value)


def build_demo_automation_policy(*, require_savings_approval: bool) -> PolicyDefinition:
    context = TrustedApplicationProfile(application="corebank", profile="legacy-browser")
    return PolicyDefinition(
        policy_id=("corebank-demo-approval" if require_savings_approval else "corebank-demo-allow"),
        version="1",
        allowed_contexts=(context,),
        rules=(
            FillPolicyRule(
                rule_id="fill-member-id",
                effect="ALLOW",
                semantic_target=semantic_target("member.search.member_id"),
            ),
            ClickPolicyRule(
                rule_id="submit-search",
                effect="ALLOW",
                semantic_target=semantic_target("member.search.submit"),
            ),
            ClickPolicyRule(
                rule_id="open-member",
                effect="ALLOW",
                semantic_target=semantic_target("member.results.open"),
            ),
            ClickPolicyRule(
                rule_id="open-savings",
                effect="REQUIRE_APPROVAL" if require_savings_approval else "ALLOW",
                semantic_target=semantic_target("member.accounts.savings"),
            ),
        ),
    )


def build_demo_operator_policy() -> PolicyDefinition:
    return PolicyDefinition(
        policy_id="corebank-demo-operator",
        version="1",
        allowed_contexts=(
            TrustedApplicationProfile(application="corebank", profile="legacy-browser"),
        ),
        rules=(
            ClickPolicyRule(
                rule_id="operator-open-savings",
                effect="ALLOW",
                semantic_target=semantic_target("member.accounts.savings"),
            ),
        ),
    )


def trusted_success_targets() -> tuple[SemanticTargetRef, ...]:
    return (
        semantic_target("member.details.identity"),
        semantic_target("member.account.type"),
        semantic_target("member.account.balance"),
    )


def build_demo_capability_request(result: DiscoveryResult) -> CapabilityBuildRequest:
    identity, account_type, balance = trusted_success_targets()
    return CapabilityBuildRequest.model_validate(
        {
            "capability_id": DEMO_CAPABILITY_ID,
            "capability_version": DEMO_CAPABILITY_VERSION,
            "name": "Lookup savings balance",
            "description": "Find a member savings account and return its balance.",
            "discovery_result": result,
            "application_requirement": {
                "application_family": "corebank",
                "surface_kind": "browser",
            },
            "input_sensitivity": [
                {
                    "action_target": {"value": "member.search.member_id"},
                    "sensitive": True,
                }
            ],
            "success_templates": (
                InputEqualitySuccessTemplate(
                    target=identity,
                    input_action_target=semantic_target("member.search.member_id"),
                ),
                LiteralEqualitySuccessTemplate(target=account_type, expected="Savings"),
                VisibleSuccessTemplate(target=balance),
            ),
            "outputs": [
                {
                    "name": "balance_minor_units",
                    "value_type": "INTEGER",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_minor_units",
                    },
                },
                {
                    "name": "currency",
                    "value_type": "CURRENCY_CODE",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_code",
                    },
                },
            ],
            "business_outcomes": [
                {
                    "code": "MEMBER_NOT_FOUND",
                    "description": "The requested member was not found.",
                    "conditions": [
                        {
                            "kind": "target_visible",
                            "target": {"value": "member.search.not_found"},
                        }
                    ],
                }
            ],
            "step_metadata": [
                {
                    "action_kind": "click",
                    "target": {"value": "member.search.submit"},
                    "postcondition": {
                        "kind": "target_visible",
                        "target": {"value": "member.results.open"},
                    },
                    "retry_policy": {
                        "kind": "wait_and_retry",
                        "max_attempts": 3,
                        "delay_ms": 400,
                    },
                }
            ],
        }
    )


def build_demo_capability() -> ValidatedCapability:
    definition = CapabilityDefinition.model_validate(
        {
            "schema_version": 1,
            "capability_id": DEMO_CAPABILITY_ID,
            "capability_version": DEMO_CAPABILITY_VERSION,
            "name": "Lookup savings balance",
            "description": "Find a member savings account and return its balance.",
            "application_requirement": {
                "application_family": "corebank",
                "surface_kind": "browser",
            },
            "inputs": [
                {
                    "name": "member_id",
                    "value_type": "STRING",
                    "required": True,
                    "sensitive": True,
                }
            ],
            "outputs": [
                {
                    "name": "balance_minor_units",
                    "value_type": "INTEGER",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_minor_units",
                    },
                },
                {
                    "name": "currency",
                    "value_type": "CURRENCY_CODE",
                    "source": {
                        "kind": "target_text",
                        "target": {"value": "member.account.balance"},
                        "parser": "currency_code",
                    },
                },
            ],
            "steps": [
                {
                    "kind": "action",
                    "step_id": "enter_member_id",
                    "action": {
                        "kind": "fill",
                        "target": {"value": "member.search.member_id"},
                        "value": {"kind": "input", "name": "member_id"},
                    },
                },
                {
                    "kind": "action",
                    "step_id": "submit_member_search",
                    "action": {
                        "kind": "click",
                        "target": {"value": "member.search.submit"},
                    },
                    "postcondition": {
                        "kind": "target_visible",
                        "target": {"value": "member.results.open"},
                    },
                    "retry_policy": {
                        "kind": "wait_and_retry",
                        "max_attempts": 3,
                        "delay_ms": 400,
                    },
                },
                {
                    "kind": "action",
                    "step_id": "open_matching_member",
                    "action": {
                        "kind": "click",
                        "target": {"value": "member.results.open"},
                    },
                },
                {
                    "kind": "action",
                    "step_id": "open_savings_account",
                    "action": {
                        "kind": "click",
                        "target": {"value": "member.accounts.savings"},
                    },
                },
            ],
            "success_conditions": [
                {
                    "kind": "target_text_equals",
                    "target": {"value": "member.details.identity"},
                    "expected": {"kind": "input", "name": "member_id"},
                },
                {
                    "kind": "target_text_equals",
                    "target": {"value": "member.account.type"},
                    "expected": {"kind": "literal", "value": "Savings"},
                },
                {
                    "kind": "target_visible",
                    "target": {"value": "member.account.balance"},
                },
            ],
            "business_outcomes": [
                {
                    "code": "MEMBER_NOT_FOUND",
                    "description": "The requested member was not found.",
                    "conditions": [
                        {
                            "kind": "target_visible",
                            "target": {"value": "member.search.not_found"},
                        }
                    ],
                }
            ],
        }
    )
    return CapabilityValidator().validate(definition)


def build_core_bank_demo_profile(entry_point: str) -> ApplicationProfile:
    frame = FrameContext(name="work-area")
    return ApplicationProfile.model_validate(
        {
            "profile_id": "corebank-demo",
            "application_family": "corebank",
            "variant": "legacy-browser",
            "entry_point": entry_point,
            "observation_rules": [
                {
                    "text": "your session has expired",
                    "outcome": "failure",
                    "summary": "Session expired",
                },
                {
                    "text": "no member found for the supplied member id",
                    "outcome": "business_outcome",
                    "summary": "Member not found",
                },
                {
                    "text": "you do not have permission to view this account",
                    "outcome": "failure",
                    "summary": "Permission denied",
                },
                {
                    "text": "no changes have been made",
                    "outcome": "business_outcome",
                    "summary": "Destructive simulation",
                },
            ],
            "target_bindings": [
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.search.member_id"),
                    frame=frame,
                    locator_candidates=(
                        RoleLocator(kind="role", role="textbox", name="Member ID", exact=True),
                        LabelLocator(kind="label", label="Member ID", exact=True),
                        CssLocator(kind="css", selector="#member_id", structural_fallback=True),
                    ),
                    description="Member ID search field",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.search.submit"),
                    frame=frame,
                    locator_candidates=(
                        RoleLocator(kind="role", role="button", name="Search", exact=True),
                        LabelLocator(kind="label", label="Search", exact=True),
                        CssLocator(
                            kind="css",
                            selector="button[type='submit']",
                            structural_fallback=True,
                        ),
                    ),
                    description="Search submission button",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.results.open"),
                    frame=frame,
                    row_scope=RowScope(
                        table_context=CssLocator(
                            kind="css",
                            selector="table",
                            structural_fallback=True,
                        ),
                        row_match=RowMatch(
                            column="Member ID",
                            value=InputValueRef(kind="input", name="member_id"),
                        ),
                    ),
                    locator_candidates=(
                        RoleLocator(kind="role", role="link", name="Open", exact=True),
                        TextLocator(kind="text", text="Open", exact=True),
                        CssLocator(
                            kind="css",
                            selector="a.button-link",
                            structural_fallback=True,
                        ),
                    ),
                    description="Search result open link",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.details.identity"),
                    frame=frame,
                    locator_candidates=(
                        CssLocator(
                            kind="css",
                            selector="#member-identity",
                            structural_fallback=True,
                        ),
                    ),
                    description="Member ID value",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.account.type"),
                    frame=frame,
                    locator_candidates=(
                        CssLocator(
                            kind="css",
                            selector="#account-type",
                            structural_fallback=True,
                        ),
                    ),
                    description="Account type value",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.accounts.savings"),
                    frame=frame,
                    row_scope=RowScope(
                        table_context=CssLocator(
                            kind="css",
                            selector="table",
                            structural_fallback=True,
                        ),
                        row_match=RowMatch(
                            column="Account Type",
                            value=LiteralValue(kind="literal", value="Savings"),
                        ),
                    ),
                    locator_candidates=(
                        RoleLocator(kind="role", role="link", name="Open", exact=True),
                        TextLocator(kind="text", text="Open", exact=True),
                        CssLocator(
                            kind="css",
                            selector="a.button-link",
                            structural_fallback=True,
                        ),
                    ),
                    description="Savings account open link",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.account.balance"),
                    frame=frame,
                    locator_candidates=(
                        CssLocator(
                            kind="css",
                            selector="#account-balance",
                            structural_fallback=True,
                        ),
                    ),
                    description="Account balance text",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.search.not_found"),
                    frame=frame,
                    locator_candidates=(
                        CssLocator(
                            kind="css",
                            selector="#member-not-found",
                            structural_fallback=True,
                        ),
                    ),
                    description="Member-not-found alert",
                ),
                BrowserTargetBinding(
                    semantic_target=SemanticTargetRef(value="member.account.close"),
                    frame=frame,
                    locator_candidates=(
                        RoleLocator(kind="role", role="button", name="Close", exact=True),
                        RoleLocator(kind="role", role="link", name="Close", exact=True),
                        TextLocator(kind="text", text="Close", exact=True),
                        CssLocator(
                            kind="css",
                            selector="a.button-link",
                            structural_fallback=True,
                        ),
                    ),
                    description="Account close link",
                ),
            ],
        }
    )
