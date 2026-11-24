"""Waits until a newly saved customer can be picked on sale documents and vouchers.

The server's party list lags behind ledger saves: on 2026-10-12 a customer saved seconds earlier was "Not
Found!" in Select Party for every case of one run, and the same customer was listed a few minutes later.
So the fixture checks Select Party on an unsaved sale bill, and retries after a pause until it is listed.
"""

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from pages.accounting.waiting import appears_within
from pages.components.bill_totals import BillTotals
from pages.dashboard_page import DashboardPage
from pages.sale.documents.bill import SaleBillDocument

ATTEMPTS = 8
# Why a fixed pause: the delay is on the server's list, which nothing on the page signals.
REFRESH_PAUSE_MS = 25_000
BILL_CLOSE_BUTTON = "[id^=btnEsc]"
BILL_CLOSE_LOOKUP_MS = 3_000


class PartyNotListedError(AssertionError):
    def __init__(self, party: str) -> None:
        waited_s = ATTEMPTS * REFRESH_PAUSE_MS // 1000
        super().__init__(f"{party} was still not in Select Party after about {waited_s} s")


class PartyAvailability:
    def __init__(self, page: Page) -> None:
        self._page = page

    def wait_until_selectable(self, party: str) -> None:
        for _ in range(ATTEMPTS):
            if self._is_selectable(party):
                return
            self._page.wait_for_timeout(REFRESH_PAUSE_MS)
        raise PartyNotListedError(party)

    def _is_selectable(self, party: str) -> bool:
        """A bill that did not open, or another screen left up, counts as not listed yet; the next attempt
        starts again from the dashboard (notifications_export setup errors, 2026-10-13)."""
        bill = SaleBillDocument(self._page)
        DashboardPage(self._page).open()
        listed = True
        try:
            bill.open_new()
            bill.choose_party(party)
        except (AssertionError, PlaywrightError):
            listed = False
        self._close_bill_if_open()
        return listed

    def _close_bill_if_open(self) -> None:
        if appears_within(self._page.locator(BILL_CLOSE_BUTTON), BILL_CLOSE_LOOKUP_MS):
            BillTotals(self._page).leave_without_saving()
