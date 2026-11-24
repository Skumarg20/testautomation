"""One customer's bill-wise receivable outstanding (`/report/outstanding/receivable/<party>`), opened with F8
from Master > Ledger as in the outstanding journey (`pages/accounting/outstanding/outstanding_report.py`).
Its toolbar is the report toolbar: Excel goes through Print Configuration (trial.balance.component.html is
its template)."""

from playwright.sync_api import expect

from pages.accounting.loader import Loader
from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from pages.masters.master_list import LedgerList

SCREEN_TIMEOUT_MS = 60_000


class PartyOutstandingPage(BasePage):
    def open_for(self, party: str) -> None:
        DashboardPage(self.page).open()
        ledgers = LedgerList(self.page)
        ledgers.open()
        ledgers.open_outstanding(party)
        expect(self.page.get_by_text(f"{party}- Outstanding", exact=True)).to_be_visible(
            timeout=SCREEN_TIMEOUT_MS
        )
        Loader(self.page).wait_until_idle()
