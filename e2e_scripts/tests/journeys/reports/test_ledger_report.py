"""J12 ledger report matches transactions (specs/ledger-report.md).

Each test owns a new bank ledger and expense ledger (`bank_book`) and posts a cheque payment of 1000.50
and a cheque receipt of 400.25 between them, so the report holds only this test's vouchers.
"""

from decimal import Decimal

import pytest

from pages.accounting.entry_date import format_for_app
from pages.banking.bank_book import BankBook
from pages.reports.ledger_report_page import LedgerReportLine, LedgerReportPage
from test_data.banking import PAYMENT_AMOUNT, RECEIPT_AMOUNT, SavedVoucher, VoucherKind

pytestmark = [pytest.mark.p1, pytest.mark.journey("ledger-report")]

NO_AMOUNT = Decimal(0)


@pytest.fixture
def vouchers(bank_book: BankBook) -> tuple[SavedVoucher, SavedVoucher]:
    """The payment and the receipt, in that order."""
    return bank_book.record(bank_book.ledgers.payment()), bank_book.record(bank_book.ledgers.receipt())


@pytest.fixture
def report(bank_book: BankBook) -> LedgerReportPage:
    return LedgerReportPage(bank_book.page)


def test_ledger_report_lists_each_voucher_with_its_amount(
    bank_book: BankBook, vouchers: tuple[SavedVoucher, SavedVoucher], report: LedgerReportPage
) -> None:
    """LR-03 (vouchers instead of a sale): the payment debits the expense ledger, the receipt credits it."""
    report.open_for(bank_book.ledgers.expense.name)

    payment, receipt = vouchers
    assert _entries(report.lines()) == [
        (format_for_app(payment.day), payment.number, VoucherKind.PAYMENT.value, PAYMENT_AMOUNT, NO_AMOUNT),
        (format_for_app(receipt.day), receipt.number, VoucherKind.RECEIPT.value, NO_AMOUNT, RECEIPT_AMOUNT),
    ]


def test_running_balance_follows_each_voucher(
    bank_book: BankBook, vouchers: tuple[SavedVoucher, SavedVoucher], report: LedgerReportPage
) -> None:
    """LR-04: balance = previous balance + debit - credit, starting from a zero opening balance."""
    report.open_for(bank_book.ledgers.expense.name)

    balances = [line.balance for line in report.lines()]
    assert balances == [PAYMENT_AMOUNT, PAYMENT_AMOUNT - RECEIPT_AMOUNT]


def test_totals_equal_the_sum_of_the_rows(
    bank_book: BankBook, vouchers: tuple[SavedVoucher, SavedVoucher], report: LedgerReportPage
) -> None:
    """LR-05: the Total row adds up the listed debits and credits and repeats the closing balance."""
    report.open_for(bank_book.ledgers.expense.name)

    lines = report.lines()
    total = report.total()
    assert (total.debit, total.credit) == (sum_of_debits(lines), sum_of_credits(lines))
    assert total.balance == lines[-1].balance


def test_bank_ledger_shows_the_same_vouchers_on_the_opposite_side(
    bank_book: BankBook, vouchers: tuple[SavedVoucher, SavedVoucher], report: LedgerReportPage
) -> None:
    """LR-23 style cross-check: the bank is credited by the payment and debited by the receipt."""
    report.open_for(bank_book.ledgers.bank.name)

    sides = [(line.voucher_type, line.debit, line.credit) for line in report.lines()]
    assert sides == [
        (VoucherKind.PAYMENT.value, NO_AMOUNT, PAYMENT_AMOUNT),
        (VoucherKind.RECEIPT.value, RECEIPT_AMOUNT, NO_AMOUNT),
    ]
    assert report.total().balance == RECEIPT_AMOUNT - PAYMENT_AMOUNT


def sum_of_debits(lines: list[LedgerReportLine]) -> Decimal:
    return sum((line.debit for line in lines), NO_AMOUNT)


def sum_of_credits(lines: list[LedgerReportLine]) -> Decimal:
    return sum((line.credit for line in lines), NO_AMOUNT)


def _entries(lines: list[LedgerReportLine]) -> list[tuple[str, str, str, Decimal, Decimal]]:
    return [(line.date, line.voucher_number, line.voucher_type, line.debit, line.credit) for line in lines]
