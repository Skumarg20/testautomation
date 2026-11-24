"""Accounting Trans. > Bank Reconciliation: bank entries of a date range and their clearing dates."""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.loader import Loader
from pages.accounting.toasts import Toasts
from pages.banking.amounts import amount_in
from pages.banking.grid_rows import GridRows
from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from test_data.banking import VoucherKind

UPDATED = re.compile(r"record updated successfully", re.IGNORECASE)
COLUMNS = ("BillDate", "DataType", "LedgerName", "InstrumentType", "InstrumentNumber", "Debit", "Credit")
CLEARING_DATE = "ClearingDateSelectedDate"
SUMMARY_LABEL_COLUMN = "InstrumentType"
COMPUTER_BALANCE = "Computer Balance"
RANGE_TO_INDEX = 1
ENTRY_TIMEOUT_MS = 30_000


@dataclass(frozen=True)
class ReconciliationEntry:
    bill_date: str
    voucher_type: str
    ledger: str
    instrument_type: str
    instrument_number: str
    debit: Decimal
    credit: Decimal
    clearing_date: str


class BankReconciliationPage(BasePage):
    def open_for(self, bank: str) -> None:
        """Shows the bank's un-cleared entries for the default range (the current month)."""
        DashboardPage(self.page).open()
        AccountingMenu(self.page).open_bank_reconciliation()
        self.page.get_by_role("combobox").first.select_option(label=bank)
        # The list loads only when Enter is pressed in the "To" date of the range.
        range_to = self._main.get_by_role("textbox").nth(RANGE_TO_INDEX)
        range_to.click()
        range_to.press("Enter")
        Loader(self.page).wait_until_idle()

    def show_cleared(self) -> None:
        self._main.get_by_role("link", name="E Cleared Entry").click()
        Loader(self.page).wait_until_idle()

    def show_uncleared(self) -> None:
        self._main.get_by_role("link", name="U Un-Cleared Entry").click()
        Loader(self.page).wait_until_idle()

    def entry(self, kind: VoucherKind, ledger: str) -> ReconciliationEntry:
        self.expect_listed(kind, ledger)
        cells = GridRows.read(self._entry_row(kind, ledger), (*COLUMNS, CLEARING_DATE))
        return ReconciliationEntry(
            bill_date=cells["BillDate"],
            voucher_type=cells["DataType"],
            ledger=cells["LedgerName"],
            instrument_type=cells["InstrumentType"],
            instrument_number=cells["InstrumentNumber"],
            debit=amount_in(cells["Debit"]),
            credit=amount_in(cells["Credit"]),
            clearing_date=cells[CLEARING_DATE],
        )

    def expect_listed(self, kind: VoucherKind, ledger: str) -> None:
        expect(self._entry_row(kind, ledger)).to_have_count(1, timeout=ENTRY_TIMEOUT_MS)

    def expect_no_entry(self, kind: VoucherKind, ledger: str) -> None:
        expect(self._entry_row(kind, ledger)).to_have_count(0, timeout=ENTRY_TIMEOUT_MS)

    def clear_with_todays_date(self, kind: VoucherKind, ledger: str) -> None:
        """Enter on an empty Clearing Date fills in the current date and saves it."""
        self._clearing_date_input(kind, ledger).press("Enter")
        Toasts(self.page).expect_success_saying(UPDATED)

    def remove_clearing_date(self, kind: VoucherKind, ledger: str) -> None:
        """Empties the Clearing Date and leaves the cell; pressing Enter instead would fill today again."""
        date_input = self._clearing_date_input(kind, ledger)
        date_input.fill("")
        date_input.dispatch_event("change")
        self._main.get_by_role("heading", name="Bank Reconciliation").click()
        Toasts(self.page).expect_success_saying(UPDATED)

    def computer_balance(self) -> Decimal:
        """The books balance of the bank shown under the list: debit positive, credit negative."""
        row = GridRows(self.page).where(SUMMARY_LABEL_COLUMN, COMPUTER_BALANCE)
        cells = GridRows.read(row, ("Debit", "Credit"))
        return amount_in(cells["Debit"]) - amount_in(cells["Credit"])

    def _entry_row(self, kind: VoucherKind, ledger: str) -> Locator:
        return GridRows(self.page).where("DataType", kind.value).filter(has_text=ledger)

    def _clearing_date_input(self, kind: VoucherKind, ledger: str) -> Locator:
        cell = self._entry_row(kind, ledger).locator(f'[col-id="{CLEARING_DATE}"]')
        cell.click()
        return cell.locator("input")

    @property
    def _main(self) -> Locator:
        return self.page.get_by_role("main")
