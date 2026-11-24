"""J29 cash transfer through a contra voucher (specs/cash-transfer-day-closure.md, scenarios CT-*).

Each test owns a new cash ledger and bank ledger (`cash_book`), so their balances start at zero and only
the test's own deposit moves them.
"""

from decimal import Decimal

import pytest

from pages.accounting.ledger_balances import LedgerPair
from pages.cash_transfer.cash_transfer_book import CashTransferBook
from pages.reports.accounting_reports import DayBookPage, DebitCredit
from pages.reports.ledger_report_page import LedgerReportPage
from test_data.cash_transfer import CHANGED_AMOUNT, DEPOSIT_AMOUNT
from test_data.money import parse_amount

# The contra takes the next tenant-wide voucher number, like tests/journeys/accounting/test_contra.py.
pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("cash-transfer-day-closure"),
    pytest.mark.xdist_group("chemist-tenant"),
]

NOTHING = Decimal(0)
UNTOUCHED = LedgerPair(NOTHING, NOTHING)
CONTRA = "Contra"
CHEQUE = "Cheque"
MISSING_CHEQUE_WARNING = "Please Fill Cheque No."


def test_cash_deposit_moves_bank_up_and_cash_down(cash_book: CashTransferBook) -> None:
    """CT-01, CT-02: Dr bank and Cr cash by the deposited amount."""
    cash_book.deposit()

    assert cash_book.balances() == LedgerPair(DEPOSIT_AMOUNT, -DEPOSIT_AMOUNT)


def test_cash_deposit_is_listed_with_its_cheque(cash_book: CashTransferBook) -> None:
    """CT-04: today's Contra Voucher List shows the cash ledger, the cheque and the amount."""
    deposit = cash_book.deposit()

    listed = cash_book.contra.listed_row(deposit)

    assert (listed["Party Name"], listed["Inst. Type."], listed["Inst. No."]) == (
        deposit.cash_ledger,
        CHEQUE,
        deposit.cheque_number,
    )
    assert parse_amount(listed["₹ Amount"]) == DEPOSIT_AMOUNT


def test_day_book_lists_both_lines_of_the_deposit(cash_book: CashTransferBook) -> None:
    """CT-03: one contra, two Day Book lines with the same voucher number."""
    deposit = cash_book.deposit()
    report = DayBookPage(cash_book.page)

    report.open()
    cash_line = report.entry_of(deposit.cash_ledger)
    bank_line = report.entry_of(deposit.bank_ledger)

    assert cash_line.voucher_type == CONTRA
    assert cash_line.amounts == DebitCredit(NOTHING, DEPOSIT_AMOUNT)
    assert bank_line.amounts == DebitCredit(DEPOSIT_AMOUNT, NOTHING)
    assert bank_line.voucher_no == cash_line.voucher_no


def test_cash_ledger_report_shows_the_deposit_as_a_credit(cash_book: CashTransferBook) -> None:
    """CT-02: the cash ledger's own report has the contra on the credit side."""
    deposit = cash_book.deposit()
    report = LedgerReportPage(cash_book.page)

    report.open_for(deposit.cash_ledger)
    lines = report.lines()

    assert [(line.voucher_type, line.debit, line.credit) for line in lines] == [
        (CONTRA, NOTHING, DEPOSIT_AMOUNT)
    ]
    assert lines[0].balance == -DEPOSIT_AMOUNT


def test_changed_amount_moves_balances_to_the_new_amount(cash_book: CashTransferBook) -> None:
    """CT-05: Modify, a new amount on both rows, Save."""
    deposit = cash_book.deposit()
    cash_book.change_amount(deposit, CHANGED_AMOUNT)

    assert cash_book.balances() == LedgerPair(CHANGED_AMOUNT, -CHANGED_AMOUNT)


def test_deleted_deposit_restores_both_balances(cash_book: CashTransferBook) -> None:
    """CT-06: after the delete both ledgers are back at zero."""
    deposit = cash_book.deposit()
    cash_book.delete(deposit)

    assert cash_book.balances() == UNTOUCHED


def test_bank_row_without_cheque_number_is_refused(cash_book: CashTransferBook) -> None:
    """CT-07: a bank row starts as Inst. Type Cheque, and Save asks for the cheque number."""
    deposit = cash_book.ledgers.deposit()
    contra = cash_book.contra
    contra.start_new()
    contra.enter_cash_leg(deposit)
    contra.enter_bank_leg_without_cheque(deposit)

    contra.save()

    contra.expect_save_refused_saying(MISSING_CHEQUE_WARNING)


def test_unequal_cash_and_bank_amounts_are_refused(cash_book: CashTransferBook) -> None:
    """CT-08: Dr total differs from Cr total; the app must not save, so neither balance moves."""
    deposit = cash_book.ledgers.deposit()
    contra = cash_book.contra
    contra.start_new()
    contra.enter_cash_leg(deposit)
    contra.enter_bank_leg(deposit.with_amount(CHANGED_AMOUNT))

    contra.save()

    contra.expect_rejected()
    assert cash_book.balances() == UNTOUCHED
