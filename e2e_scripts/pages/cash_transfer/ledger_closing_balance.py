"""The closing balance of one ledger, read from its transaction report (pages/reports/ledger_report_page).

The shared report page waits for the "Total" row, which a ledger without vouchers does not have (seen
live: only the column headers and empty rows). This page also reads that empty case, as zero.
"""

from decimal import Decimal

from playwright.sync_api import expect

from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.list_screen import ListScreen
from pages.accounting.loader import Loader
from pages.accounting.waiting import appears_within
from pages.dashboard_page import DashboardPage
from pages.reports.ledger_report_page import LedgerReportPage

NO_BALANCE = Decimal(0)
REPORT_TIMEOUT_MS = 30_000
# Long enough for a slow report to render its rows, so "no Total row" really means no vouchers.
TOTAL_ROW_LOOKUP_MS = 15_000


class LedgerClosingBalance(LedgerReportPage):
    def of(self, ledger: str) -> Decimal:
        """The running balance after the ledger's last voucher (debit positive); zero without vouchers."""
        self._open_report(ledger)
        if not appears_within(self._total_row, TOTAL_ROW_LOOKUP_MS):
            return NO_BALANCE
        lines = self.lines()
        return lines[-1].balance if lines else NO_BALANCE

    def _open_report(self, ledger: str) -> None:
        DashboardPage(self.page).open()
        AccountingMenu(self.page).open_ledger_list()
        ListScreen(self.page).search(ledger)
        self.page.get_by_role("gridcell", name=ledger, exact=True).first.dblclick()
        expect(self.page.get_by_role("heading", name=f"Ledger : {ledger}")).to_be_visible(
            timeout=REPORT_TIMEOUT_MS
        )
        expect(self.page.get_by_role("columnheader", name="₹ Balance")).to_be_visible(
            timeout=REPORT_TIMEOUT_MS
        )
        Loader(self.page).wait_until_idle()
