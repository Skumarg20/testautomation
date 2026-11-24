"""Offline checks of the accounting helpers: date resolution, balance parsing and the case data."""

from datetime import date
from decimal import Decimal

import pytest

from pages.accounting.entry_date import format_for_app, is_today, resolve_entry_date
from pages.accounting.ledger_balances import signed_balance
from pages.accounting.voucher_cases import load_cases, single_sided_case, two_sided_case

pytestmark = pytest.mark.framework
SHEET_SIZES = {"receipt": 5, "payment": 5, "debit-note": 6, "credit-note": 6, "contra": 6, "journal": 6}


def test_today_resolves_to_the_current_date() -> None:
    assert is_today(resolve_entry_date("today"))


def test_compact_sheet_date_is_written_the_way_the_app_expects() -> None:
    assert format_for_app(resolve_entry_date("20250101")) == "01-01-2025"
    assert resolve_entry_date("20250101") == date(2025, 1, 1)


@pytest.mark.parametrize(
    ("shown", "expected"),
    [("5,000.00 Dr", "5000.00"), ("250.50 Cr", "-250.50"), ("0.00", "0.00"), ("", "0")],
)
def test_signed_balance_reads_debit_positive_and_credit_negative(shown: str, expected: str) -> None:
    assert signed_balance(shown) == Decimal(expected)


@pytest.mark.parametrize("sheet", SHEET_SIZES)
def test_every_sheet_keeps_all_its_cases(sheet: str) -> None:
    assert len(load_cases(sheet)) == SHEET_SIZES[sheet]


def test_empty_cells_stay_in_their_own_column() -> None:
    receipt = single_sided_case(load_cases("receipt")[2], "delete_receipt")
    assert receipt.leg.account == ""
    assert receipt.leg.amount == "5000"


def test_credit_first_sheets_enter_the_credit_account_in_row_zero() -> None:
    credit_note = two_sided_case(load_cases("credit-note")[0], "credit", "delete_credit_note")
    assert (credit_note.first.side, credit_note.first.account) == ("credit", "Cash Account")
    assert credit_note.delete_after
