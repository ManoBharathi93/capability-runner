"""Immutable synthetic fixtures for the banking target application."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

AccountType = Literal["savings", "checking"]
MemberStatus = Literal["Active", "Restricted"]
ScenarioMode = Literal["normal", "slow_search", "session_expired", "login_required"]


@dataclass(frozen=True, slots=True)
class AccountFixture:
    account_type: AccountType
    status: str
    balance_minor_units: int
    currency: str = "USD"


@dataclass(frozen=True, slots=True)
class MemberFixture:
    member_id: str
    name: str
    status: MemberStatus
    accounts: tuple[AccountFixture, ...]

    def get_account(self, account_type: AccountType) -> AccountFixture | None:
        for account in self.accounts:
            if account.account_type == account_type:
                return account
        return None


MEMBERS = MappingProxyType(
    {
        "12345": MemberFixture(
            member_id="12345",
            name="Avery Morgan",
            status="Active",
            accounts=(
                AccountFixture("savings", "Open", 438221),
                AccountFixture("checking", "Open", 15840),
            ),
        ),
        "67890": MemberFixture(
            member_id="67890",
            name="Jordan Lee",
            status="Active",
            accounts=(
                AccountFixture("savings", "Open", 98765),
                AccountFixture("checking", "Open", 5120),
            ),
        ),
        "55555": MemberFixture(
            member_id="55555",
            name="Casey Rivera",
            status="Restricted",
            accounts=(
                AccountFixture("savings", "Restricted", 120000),
                AccountFixture("checking", "Restricted", 4500),
            ),
        ),
    }
)


def get_member(member_id: str) -> MemberFixture | None:
    return MEMBERS.get(member_id)
