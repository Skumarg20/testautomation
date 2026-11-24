"""The transaction report of one ledger, opened from the ledger master list (Enter / double click)."""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.list_screen import ListScreen
from pages.banking.amounts import amount_in, balance_in
from pages.banking.grid_rows import GridRows
from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage

COLUMNS = ("Date", "VoucherNo", "VoucherType", "Debit", "Credit", "ClosingBalance")
ENTRY_DATE = re.compile(r"\d{2}-\d{2}-\d{4}")
TOTAL = "Total"
REPORT_TIMEOUT_MS = 30_000
MODIFY_VOUCHER = re.compile(r"^Modify (Payment|Receipt) Voucher")


@dataclass(frozen=True)
class LedgerReportLine:
    """One row of the report. `balance` is the running balance after the row: debit positive."""

    date: str
    voucher_number: str
    voucher_type: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class LedgerReportPage(BasePage):
    def open_for(self, ledger: str) -> None:
        DashboardPage(self.page).open()
        AccountingMenu(self.page).open_ledger_list()
        ListScreen(self.page).search(ledger)
        self.page.get_by_role("gridcell", name=ledger, exact=True).first.dblclick()
        expect(self.page.get_by_role("heading", name=f"Ledger : {ledger}")).to_be_visible(
            timeout=REPORT_TIMEOUT_MS
        )
        expect(self._total_row).to_be_visible(timeout=REPORT_TIMEOUT_MS)

    def open_voucher(self, ledger: str, voucher_number: str) -> None:
        """Drills down from the report row into the voucher (Modify Payment/Receipt Voucher)."""
        self.open_for(ledger)
        self.page.get_by_role("gridcell", name=voucher_number, exact=True).first.dblclick()
        expect(self.page.get_by_text(MODIFY_VOUCHER)).to_be_visible(timeout=REPORT_TIMEOUT_MS)

    def voucher_numbers(self, ledger: str, voucher_type: str) -> list[str]:
        """Numbers of one voucher type only: payments and receipts are numbered in separate series."""
        self.open_for(ledger)
        return [line.voucher_number for line in self.lines() if line.voucher_type == voucher_type]

    def lines(self) -> list[LedgerReportLine]:
        """The voucher rows in screen order (opening and total rows excluded)."""
        rows = GridRows(self.page).where("Date", ENTRY_DATE)
        ordered = sorted(rows.all(), key=_row_index)
        return [_line_of(row) for row in ordered]

    def total(self) -> LedgerReportLine:
        return _line_of(self._total_row)

    @property
    def _total_row(self) -> Locator:
        return GridRows(self.page).where("Date", TOTAL).first


def _row_index(row: Locator) -> int:
    return int(row.get_attribute("row-index") or 0)


def _line_of(row: Locator) -> LedgerReportLine:
    cells = GridRows.read(row, COLUMNS)
    return LedgerReportLine(
        date=cells["Date"],
        voucher_number=cells["VoucherNo"],
        voucher_type=cells["VoucherType"],
        debit=amount_in(cells["Debit"]),
        credit=amount_in(cells["Credit"]),
        balance=balance_in(cells["ClosingBalance"]),
    )
