"""Report "Close Billing/Day" (/closingDayReport) of the Daily Cashbook, read only.

The screen only reads: it has no close button of its own (closing and approval happen in the Daily
Cashbook screens, which this tenant does not authorize; see specs/cash-transfer-day-closure.md).
"""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.loader import Loader
from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage

TITLE = "Close Billing/Day"
CLOSING_DATE = re.compile(r"Closing Date : (\d{2}-\d{2}-\d{4})")
NOT_AUTHORIZED = "Oops! You are not authorized."
SCREEN_TIMEOUT_MS = 60_000


class CloseBillingDayPage(BasePage):
    PATH = "/closingDayReport"

    def open(self) -> None:
        DashboardPage(self.page).open()
        self.goto(self.PATH, SCREEN_TIMEOUT_MS)
        Loader(self.page).wait_until_idle()
        expect(self.page.get_by_role("heading", name=TITLE, level=1)).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def closing_date(self) -> str:
        text = self.page.get_by_text(CLOSING_DATE).first
        expect(text).to_be_visible(timeout=SCREEN_TIMEOUT_MS)
        found = CLOSING_DATE.search(text.inner_text())
        assert found, f"{self.PATH}: no closing date in {text.inner_text()!r}"
        return found.group(1)

    def date_range(self) -> tuple[str, str]:
        """The From and To boxes of "Selected Date Range"."""
        boxes = self.page.get_by_role("textbox")
        expect(boxes.nth(1)).to_be_visible(timeout=SCREEN_TIMEOUT_MS)
        return boxes.nth(0).input_value(), boxes.nth(1).input_value()

    @property
    def approvals_button(self) -> Locator:
        return self.page.get_by_role("button", name="Go to manage Approvals")


class DailyCashbookScreen(BasePage):
    """Any Daily Cashbook route; tells whether the app renders it or its not-authorized page."""

    def open(self, path: str) -> None:
        DashboardPage(self.page).open()
        self.goto(path, SCREEN_TIMEOUT_MS)
        Loader(self.page).wait_until_idle()

    @property
    def not_authorized_message(self) -> Locator:
        return self.page.get_by_text(NOT_AUTHORIZED)
