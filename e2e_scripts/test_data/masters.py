"""Test-owned account groups and ledgers for the master CRUD journeys (J07 `masters`, J17)."""

from dataclasses import dataclass, replace
from itertools import count

# Masters seen on the garments QA company 2026-10-08 (specs/masters.md); tests pick them, never create them.
SUNDRY_DEBTORS = "Sundry Debtors"
SUNDRY_CREDITORS = "Sundry Creditors"
INDIRECT_EXPENSES = "Indirect Expenses"
PARTY_STATION = "Others"
MOBILE_DIGITS = 9
MOBILE_LEADING_DIGIT = "9"
HEX_BASE = 16


@dataclass(frozen=True)
class AccountGroupSpec:
    name: str
    parent: str


@dataclass(frozen=True)
class GeneralLedgerSpec:
    """A ledger outside the party groups: its form asks only for a name and an account group."""

    name: str
    group: str


@dataclass(frozen=True)
class PartyLedgerSpec:
    """A customer or supplier ledger with the fields the QA company makes mandatory."""

    name: str
    group: str
    station: str
    mobile: str

    def renamed(self, name: str) -> "PartyLedgerSpec":
        return replace(self, name=name)


class MasterDataFactory:
    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._serial = count(1)

    def account_group(self, parent: str = INDIRECT_EXPENSES) -> AccountGroupSpec:
        return AccountGroupSpec(self._unique_name("Grp"), parent)

    def general_ledger(self, group: str) -> GeneralLedgerSpec:
        return GeneralLedgerSpec(self._unique_name("Exp"), group)

    def customer(self) -> PartyLedgerSpec:
        return self._party("Cust", SUNDRY_DEBTORS)

    def supplier(self) -> PartyLedgerSpec:
        return self._party("Supp", SUNDRY_CREDITORS)

    def _party(self, label: str, group: str) -> PartyLedgerSpec:
        return PartyLedgerSpec(self._unique_name(label), group, PARTY_STATION, self._mobile())

    def _unique_name(self, label: str) -> str:
        return f"QA-{self._run_id}-{label}-{next(self._serial)}"

    def _mobile(self) -> str:
        """Ten digits starting with 9, derived from the run id so parallel runs differ."""
        digits = int(self._run_id, HEX_BASE) % 10**MOBILE_DIGITS
        return f"{MOBILE_LEADING_DIGIT}{digits:0{MOBILE_DIGITS}d}"
