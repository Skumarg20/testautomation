"""J11 bank entry and bank reconciliation (specs/bank-entry-reconciliation.md).

Each test owns a new bank ledger and expense ledger (`bank_book`), so no other test moves their balances.
"""

from decimal import Decimal

import pytest

from pages.accounting.entry_date import format_for_app
from pages.banking.bank_book import BankBook
from pages.banking.bank_voucher import BankVoucher
from pages.reports.ledger_report_page import LedgerReportPage
from test_data.banking import PAYMENT_AMOUNT, RECEIPT_AMOUNT, VoucherKind

pytestmark = [pytest.mark.p1, pytest.mark.journey("bank-entry-reconciliation")]

NO_AMOUNT = Decimal(0)
NOT_CLEARED = ""
CHEQUE = "Cheque"


def test_bank_payment_is_listed_unreconciled_with_its_cheque(bank_book: BankBook) -> None:
    """BK-01, BK-17: a cheque payment shows on the Debit (withdrawal) side of the bank statement view."""
    payment = bank_book.ledgers.payment()
    voucher = bank_book.record(payment)

    entry = bank_book.reconciliation().entry(VoucherKind.PAYMENT, payment.account)

    assert (entry.bill_date, entry.instrument_type, entry.instrument_number) == (
        format_for_app(voucher.day),
        CHEQUE,
        payment.cheque_number,
    )
    assert (entry.debit, entry.credit, entry.clearing_date) == (PAYMENT_AMOUNT, NO_AMOUNT, NOT_CLEARED)


def test_bank_receipt_is_listed_on_the_credit_side(bank_book: BankBook) -> None:
    """BK-02, BK-17: a cheque receipt shows on the Credit (deposit) side, not yet cleared."""
    receipt = bank_book.ledgers.receipt()
    bank_book.record(receipt)

    entry = bank_book.reconciliation().entry(VoucherKind.RECEIPT, receipt.account)

    assert (entry.debit, entry.credit, entry.clearing_date) == (NO_AMOUNT, RECEIPT_AMOUNT, NOT_CLEARED)
    assert entry.instrument_number == receipt.cheque_number


def test_clearing_date_moves_entry_to_the_cleared_view(bank_book: BankBook) -> None:
    """BK-18, BK-21, BK-22: Enter on an empty Clearing Date clears the entry with today's date."""
    payment, receipt = bank_book.ledgers.payment(), bank_book.ledgers.receipt()
    bank_book.record(payment)
    bank_book.record(receipt)
    cleared_on = bank_book.clear(VoucherKind.PAYMENT)

    reconciliation = bank_book.reconciliation()
    reconciliation.expect_listed(VoucherKind.RECEIPT, receipt.account)
    reconciliation.expect_no_entry(VoucherKind.PAYMENT, payment.account)
    reconciliation.show_cleared()

    cleared = reconciliation.entry(VoucherKind.PAYMENT, payment.account)
    assert cleared.clearing_date == format_for_app(cleared_on)


def test_removing_the_clearing_date_returns_entry_to_uncleared(bank_book: BankBook) -> None:
    """BK-23: an entry cleared by mistake goes back to the un-cleared list when its date is removed."""
    payment = bank_book.ledgers.payment()
    bank_book.record(payment)
    bank_book.clear(VoucherKind.PAYMENT)
    bank_book.remove_clearing(VoucherKind.PAYMENT)

    entry = bank_book.reconciliation().entry(VoucherKind.PAYMENT, payment.account)

    assert entry.clearing_date == NOT_CLEARED


def test_reconciled_voucher_cannot_be_deleted(bank_book: BankBook) -> None:
    """BK-15 (Q3): deleting a cleared payment is refused with the clearing date in the message."""
    payment = bank_book.ledgers.payment()
    voucher = bank_book.record(payment)
    cleared_on = bank_book.clear(VoucherKind.PAYMENT)

    BankVoucher(bank_book.page).expect_delete_refused_as_reconciled(voucher, cleared_on)


def test_computer_balance_equals_the_bank_ledger_closing_balance(bank_book: BankBook) -> None:
    """BK-31 (books side): the Computer Balance under the list equals the bank ledger's closing balance."""
    payment = bank_book.ledgers.payment()
    bank_book.record(payment)
    bank_book.record(bank_book.ledgers.receipt())

    reconciliation = bank_book.reconciliation()
    reconciliation.expect_listed(VoucherKind.PAYMENT, payment.account)
    computer_balance = reconciliation.computer_balance()
    ledger_report = LedgerReportPage(bank_book.page)
    ledger_report.open_for(bank_book.ledgers.bank.name)

    assert computer_balance == RECEIPT_AMOUNT - PAYMENT_AMOUNT
    assert ledger_report.total().balance == computer_balance
