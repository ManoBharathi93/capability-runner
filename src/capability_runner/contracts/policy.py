"""Typed policy contracts for trusted action authorization.

Policy decisions stay separate from execution. The guard consumes typed action
requests plus trusted application/profile context and returns a bounded
decision without dispatching surface actions.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .surfaces import SemanticTargetRef


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


PolicyDecisionType = Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
PolicyEffect = Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
PolicyReasonCode = Literal[
    "ALLOWED_BY_RULE",
    "UNKNOWN_APPLICATION",
    "ACTION_NOT_ALLOWED",
    "TARGET_NOT_ALLOWED",
    "DESTINATION_NOT_ALLOWED",
    "APPROVAL_REQUIRED",
    "MALFORMED_ACTION",
    "NO_MATCHING_RULE",
]


class PolicyContext(ContractModel):
    application: str = Field(min_length=1, max_length=80)
    profile: str = Field(min_length=1, max_length=80)


class TrustedApplicationProfile(ContractModel):
    application: str = Field(min_length=1, max_length=80)
    profile: str = Field(min_length=1, max_length=80)


class AllowedDestination(ContractModel):
    scheme: Literal["http", "https"]
    hostname: str = Field(min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    path: str = Field(default="/", min_length=1, max_length=2048)

    @field_validator("scheme")
    @classmethod
    def _normalize_scheme(cls, value: str) -> str:
        return value.casefold()

    @field_validator("hostname")
    @classmethod
    def _normalize_hostname(cls, value: str) -> str:
        normalized = value.casefold().strip()
        if not normalized:
            raise ValueError("hostname must not be empty")
        return normalized

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("path must start with '/'")
        if "?" in value or "#" in value:
            raise ValueError("path must not include query or fragment")
        return value


class ClickPolicyRule(ContractModel):
    action_kind: Literal["click"] = "click"
    rule_id: str = Field(min_length=1, max_length=80)
    effect: PolicyEffect
    semantic_target: SemanticTargetRef


class FillPolicyRule(ContractModel):
    action_kind: Literal["fill"] = "fill"
    rule_id: str = Field(min_length=1, max_length=80)
    effect: PolicyEffect
    semantic_target: SemanticTargetRef


class NavigatePolicyRule(ContractModel):
    action_kind: Literal["navigate"] = "navigate"
    rule_id: str = Field(min_length=1, max_length=80)
    effect: PolicyEffect
    destination: AllowedDestination


class WaitPolicyRule(ContractModel):
    action_kind: Literal["wait"] = "wait"
    rule_id: str = Field(min_length=1, max_length=80)
    effect: PolicyEffect


type PolicyRule = Annotated[
    ClickPolicyRule | FillPolicyRule | NavigatePolicyRule | WaitPolicyRule,
    Field(discriminator="action_kind"),
]


class PolicyDefinition(ContractModel):
    policy_id: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    allowed_contexts: tuple[TrustedApplicationProfile, ...] = Field(default_factory=tuple)
    rules: tuple[PolicyRule, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_unique_rules(self) -> PolicyDefinition:
        seen: set[tuple[object, ...]] = set()
        for rule in self.rules:
            key = _rule_key(rule)
            if key in seen:
                raise ValueError("duplicate policy rules are not allowed")
            seen.add(key)
        return self


class PolicyDecision(ContractModel):
    decision: PolicyDecisionType
    reason_code: PolicyReasonCode
    summary: str = Field(min_length=1, max_length=160)
    rule_id: str | None = Field(default=None, min_length=1, max_length=80)


def _rule_key(rule: PolicyRule) -> tuple[object, ...]:
    if isinstance(rule, ClickPolicyRule):
        return (rule.action_kind, rule.semantic_target.value)
    if isinstance(rule, FillPolicyRule):
        return (rule.action_kind, rule.semantic_target.value)
    if isinstance(rule, NavigatePolicyRule):
        destination = rule.destination
        return (
            rule.action_kind,
            destination.scheme,
            destination.hostname,
            destination.port,
            destination.path,
        )
    return (rule.action_kind,)
