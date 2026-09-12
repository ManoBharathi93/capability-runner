"""Deterministic policy evaluation for trusted actions.

The guard is pure: it evaluates typed actions against trusted policy
configuration and returns an authorization decision. It does not execute the
action, dispatch to a browser, or record evidence.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from pydantic import HttpUrl

from capability_runner.contracts.actions import (
    ActionSpec,
    ClickAction,
    FillAction,
    NavigateAction,
)
from capability_runner.contracts.browser_discovery import BrowserScope, InteractiveElement
from capability_runner.contracts.policy import (
    AllowedDestination,
    ClickPolicyRule,
    FillPolicyRule,
    NavigatePolicyRule,
    PolicyContext,
    PolicyDecision,
    PolicyDecisionType,
    PolicyDefinition,
    PolicyEffect,
    PolicyReasonCode,
    WaitPolicyRule,
)
from capability_runner.contracts.surfaces import SemanticTargetRef
from capability_runner.surfaces.browser_observation import method_allowed


def observed_action_allowed(element: InteractiveElement, scope: BrowserScope) -> bool:
    """Only an operator-attested read-only route can authorize a new-app action."""
    if not element.enabled or element.match_count != 1:
        return False
    if re.search(
        r"\b(delete|remove|close|transfer|submit payment|purchase|send|logout|"
        r"sign out|disable|erase|reset|terminate)\b",
        element.accessible_name,
        re.IGNORECASE,
    ):
        return False
    if element.action_kind not in {"fill", "click"}:
        return False
    return element.destination is not None and method_allowed(
        element.method, element.destination, scope
    )


_DEFAULT_PORTS = {"http": 80, "https": 443}


class PolicyGuard:
    def __init__(self, policy_definition: PolicyDefinition) -> None:
        self._policy_definition = policy_definition

    def evaluate(
        self,
        action: ActionSpec,
        context: PolicyContext,
        semantic_target: SemanticTargetRef | None = None,
    ) -> PolicyDecision:
        if not self._is_allowed_context(context):
            return self._decision(
                "DENY",
                "UNKNOWN_APPLICATION",
                "Application/profile is not approved.",
            )

        if isinstance(action, ClickAction):
            rule = self._match_click_rule(semantic_target)
            if rule is None:
                return self._decision(
                    "DENY",
                    "TARGET_NOT_ALLOWED",
                    "Target is not allowed by policy.",
                )
            return self._decision_from_rule(rule.effect, rule.rule_id, "click target")

        if isinstance(action, FillAction):
            rule = self._match_fill_rule(semantic_target)
            if rule is None:
                return self._decision(
                    "DENY",
                    "TARGET_NOT_ALLOWED",
                    "Target is not allowed by policy.",
                )
            return self._decision_from_rule(rule.effect, rule.rule_id, "fill target")

        if isinstance(action, NavigateAction):
            rule = self._match_navigate_rule(action.url)
            if rule is None:
                return self._decision(
                    "DENY",
                    "DESTINATION_NOT_ALLOWED",
                    "Destination is not allowed by policy.",
                )
            return self._decision_from_rule(rule.effect, rule.rule_id, "destination")

        rule = self._match_wait_rule()
        if rule is None:
            return self._decision(
                "DENY",
                "ACTION_NOT_ALLOWED",
                "Action is not allowed by policy.",
            )
        return self._decision_from_rule(rule.effect, rule.rule_id, "action")

        return self._decision("DENY", "MALFORMED_ACTION", "Action is not recognized.")

    def _is_allowed_context(self, context: PolicyContext) -> bool:
        return any(
            allowed.application == context.application and allowed.profile == context.profile
            for allowed in self._policy_definition.allowed_contexts
        )

    def _match_click_rule(
        self, semantic_target: SemanticTargetRef | None
    ) -> ClickPolicyRule | None:
        if semantic_target is None:
            return None
        for rule in self._policy_definition.rules:
            if isinstance(rule, ClickPolicyRule) and rule.semantic_target == semantic_target:
                return rule
        return None

    def _match_fill_rule(self, semantic_target: SemanticTargetRef | None) -> FillPolicyRule | None:
        if semantic_target is None:
            return None
        for rule in self._policy_definition.rules:
            if isinstance(rule, FillPolicyRule) and rule.semantic_target == semantic_target:
                return rule
        return None

    def _match_navigate_rule(self, url: HttpUrl) -> NavigatePolicyRule | None:
        for rule in self._policy_definition.rules:
            if isinstance(rule, NavigatePolicyRule) and _destination_matches(rule.destination, url):
                return rule
        return None

    def _match_wait_rule(self) -> WaitPolicyRule | None:
        for rule in self._policy_definition.rules:
            if isinstance(rule, WaitPolicyRule):
                return rule
        return None

    def _decision(
        self,
        decision: PolicyDecisionType,
        reason_code: PolicyReasonCode,
        summary: str,
        rule_id: str | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            decision=decision,
            reason_code=reason_code,
            summary=summary,
            rule_id=rule_id,
        )

    def _decision_from_rule(
        self,
        effect: PolicyEffect,
        rule_id: str,
        subject: str,
    ) -> PolicyDecision:
        if effect == "ALLOW":
            return self._decision(
                "ALLOW",
                "ALLOWED_BY_RULE",
                f"Allowed by {subject} rule.",
                rule_id,
            )
        if effect == "REQUIRE_APPROVAL":
            return self._decision(
                "REQUIRE_APPROVAL",
                "APPROVAL_REQUIRED",
                f"{subject.capitalize()} requires approval.",
                rule_id,
            )
        return self._decision(
            "DENY",
            "ACTION_NOT_ALLOWED",
            f"{subject.capitalize()} is denied by policy.",
            rule_id,
        )


def _destination_matches(destination: AllowedDestination, url: object) -> bool:
    parts = urlsplit(str(url))
    if parts.scheme.casefold() not in {"http", "https"}:
        return False
    if parts.username is not None or parts.password is not None:
        return False
    if not parts.hostname:
        return False
    host = parts.hostname.casefold()
    if host != destination.hostname:
        return False

    port = parts.port if parts.port is not None else _DEFAULT_PORTS.get(parts.scheme.casefold())
    expected_port = (
        destination.port if destination.port is not None else _DEFAULT_PORTS.get(destination.scheme)
    )
    if port != expected_port:
        return False

    path = parts.path or "/"
    return path == destination.path and parts.scheme.casefold() == destination.scheme
