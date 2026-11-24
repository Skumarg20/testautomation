"""The bank ledgers and vouchers one test owns, and how to undo them after the test."""

from datetime import date
from functools import partial

from playwright.sync_api import Page

from pages.banking.bank_reconciliation_page import BankReconciliationPage
from pages.banking.bank_voucher import BankVoucher
from pages.banking.ledger_setup import LedgerSetup
from pages.components.undo import UndoStep, undo_all
from pages.reports.ledger_report_page import LedgerReportPage
from test_data.banking import BankEntry, BankLedgers, SavedVoucher, VoucherKind


class BankBook:
    """Creates through the UI and remembers what it created, because the app refuses to delete a
    ledger with vouchers or a voucher that is reconciled: undo runs in the reverse order."""

    def __init__(self, page: Page, ledgers: BankLedgers) -> None:
        self.ledgers = ledgers
        self.page = page
        self._vouchers: list[SavedVoucher] = []
        self._cleared: list[VoucherKind] = []
        self._created_ledgers: list[str] = []

    def open(self) -> None:
        setup = LedgerSetup(self.page)
        for ledger in (self.ledgers.bank, self.ledgers.expense):
            setup.create(ledger)
            self._created_ledgers.append(ledger.name)

    def record(self, entry: BankEntry) -> SavedVoucher:
        """Saves the voucher and reads its number back from the account's ledger report, where it is
        the only number of its type this book does not know yet (the ledger is new, so all its vouchers
        are ours)."""
        day = date.today()
        BankVoucher(self.page).record(entry, self.ledgers.bank.name)
        known = {voucher.number for voucher in self._vouchers if voucher.kind == entry.kind}
        listed = LedgerReportPage(self.page).voucher_numbers(entry.account, entry.kind.value)
        new_numbers = [number for number in listed if number not in known]
        assert len(new_numbers) == 1, f"Expected one new voucher in {entry.account}, found {new_numbers}"
        voucher = SavedVoucher(entry.kind, new_numbers[0], entry.account, day)
        self._vouchers.append(voucher)
        return voucher

    def clear(self, kind: VoucherKind) -> date:
        """Clears the entry with the app's current date and returns that date."""
        day = date.today()
        reconciliation = self.reconciliation()
        reconciliation.clear_with_todays_date(kind, self.ledgers.expense.name)
        self._cleared.append(kind)
        return day

    def remove_clearing(self, kind: VoucherKind) -> None:
        reconciliation = self.reconciliation()
        reconciliation.show_cleared()
        reconciliation.remove_clearing_date(kind, self.ledgers.expense.name)
        self._cleared.remove(kind)

    def reconciliation(self) -> BankReconciliationPage:
        """The reconciliation screen, freshly opened for this book's bank."""
        page = BankReconciliationPage(self.page)
        page.open_for(self.ledgers.bank.name)
        return page

    def close(self) -> None:
        undo_all([*self._clearing_undos(), *self._voucher_undos(), *self._ledger_undos()])

    def _clearing_undos(self) -> list[UndoStep]:
        return [
            (f"clearing of the {kind.value}", partial(self.remove_clearing, kind)) for kind in self._cleared
        ]

    def _voucher_undos(self) -> list[UndoStep]:
        vouchers = BankVoucher(self.page)
        return [
            (f"{voucher.kind.value} {voucher.number}", partial(vouchers.delete, voucher))
            for voucher in reversed(self._vouchers)
        ]

    def _ledger_undos(self) -> list[UndoStep]:
        setup = LedgerSetup(self.page)
        return [(f"ledger {name}", partial(setup.delete, name)) for name in reversed(self._created_ledgers)]
