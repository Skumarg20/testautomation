"""Test-case rows of the accounting sheets, turned into typed values the voucher flows use."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from pages.accounting.entry_date import resolve_entry_date
from pages.accounting.voucher_grid import Column
from test_data.document_cases import DocumentCase, cases_for

Side = Literal["debit", "credit"]
SIDE_COLUMN: dict[Side, Column] = {"debit": "drAmount", "credit": "crAmount"}
MINIMUM_AMOUNT = Decimal(1)
NO_AMOUNT = "0"
DELETE_YES = "Y"


@dataclass(frozen=True)
class Leg:
    """One line of a voucher: the account, which side it is on and the amount typed as in the sheet."""

    side: Side
    account: str
    amount: str

    @property
    def column(self) -> Column:
        return SIDE_COLUMN[self.side]

    @property
    def value(self) -> Decimal:
        return Decimal(self.amount)

    @property
    def is_below_minimum(self) -> bool:
        return self.value < MINIMUM_AMOUNT


@dataclass(frozen=True)
class SingleSidedCase:
    """Receipt or payment: one account with an amount and an optional short amount."""

    id: str
    is_negative: bool
    day: date
    leg: Leg
    short_amount: str
    narration: str
    delete_after: bool

    @property
    def total(self) -> Decimal:
        return self.leg.value + Decimal(self.short_amount)


@dataclass(frozen=True)
class TwoSidedCase:
    """Debit note, credit note, contra or journal: two accounts, entered in row 0 and row 1."""

    id: str
    is_negative: bool
    day: date
    first: Leg
    second: Leg
    narration: str
    delete_after: bool

    @property
    def has_both_accounts(self) -> bool:
        return bool(self.first.account and self.second.account)

    @property
    def debit_leg(self) -> Leg:
        return self.first if self.first.side == "debit" else self.second

    @property
    def credit_leg(self) -> Leg:
        return self.first if self.first.side == "credit" else self.second


def load_cases(sheet: str) -> list[DocumentCase]:
    return cases_for("accounting", sheet)


def single_sided_case(case: DocumentCase, delete_key: str) -> SingleSidedCase:
    values = case.inputs
    return SingleSidedCase(
        id=case.id,
        is_negative=case.is_negative,
        day=resolve_entry_date(values["entry_date"]),
        leg=Leg("debit", values.get("account_name", ""), values.get("amount", NO_AMOUNT)),
        short_amount=values.get("short_amount", NO_AMOUNT),
        narration=values.get("narration", ""),
        delete_after=values.get(delete_key) == DELETE_YES,
    )


def two_sided_case(case: DocumentCase, first_side: Side, delete_key: str) -> TwoSidedCase:
    values = case.inputs
    debit = Leg("debit", values.get("dr_account_name", ""), values.get("debit_amount", NO_AMOUNT))
    credit = Leg("credit", values.get("cr_account_name", ""), values.get("credit_amount", NO_AMOUNT))
    first, second = (debit, credit) if first_side == "debit" else (credit, debit)
    return TwoSidedCase(
        id=case.id,
        is_negative=case.is_negative,
        day=resolve_entry_date(values["entry_date"]),
        first=first,
        second=second,
        narration=values.get("narration", ""),
        delete_after=values.get(delete_key) == DELETE_YES,
    )
