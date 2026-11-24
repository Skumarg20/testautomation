"""CRM > Loyalty Management System: the company's one loyalty setup (/crm/loyalty/create-loyalty).

The setup is a single record per company: the screen saves it the first time and updates it after
that; the app offers no delete (spec N3).
"""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.confirmation import Confirmation
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.crm.crm_menu import CrmMenu
from pages.dashboard_page import DashboardPage
from test_data.loyalty import LoyaltyEarning

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
UPDATED_MESSAGE = re.compile("Record Updated Successfully", re.IGNORECASE)
MISSING_DETAILS = re.compile("Please Enter The Required Details!", re.IGNORECASE)
CLOSE_QUESTION = "Are you sure you want to close?"
SCREEN_TIMEOUT_MS = 60_000


class LoyaltySetup(BasePage):
    def open_from_menu(self) -> None:
        """Waits for the saved setup: the button reads Update once it has loaded."""
        CrmMenu(self.page).open_loyalty_setup()
        expect(self.page.get_by_role("heading", name="Loyalty Setup", level=1)).to_be_visible(
            timeout=SCREEN_TIMEOUT_MS
        )
        expect(self._update_button).to_be_visible(timeout=SCREEN_TIMEOUT_MS)
        expect(self._points).not_to_have_value("", timeout=SCREEN_TIMEOUT_MS)

    def reopen(self) -> None:
        """From the dashboard: the menu does not reload the screen when it is already open."""
        DashboardPage(self.page).open()
        self.open_from_menu()

    def current_earning(self) -> LoyaltyEarning:
        return LoyaltyEarning(self._amount.input_value(), self._points.input_value())

    def enter_earning(self, earning: LoyaltyEarning) -> None:
        self._amount.fill(earning.amount)
        self._points.fill(earning.points)

    def clear_amount(self) -> None:
        """Key by key: the decimal input mask ignores `fill("")` and a select-all Backspace."""
        self._amount.click()
        self.page.keyboard.press("End")
        for _ in self._amount.input_value():
            self.page.keyboard.press("Backspace")
        expect(self._amount).to_have_value("")

    def update(self) -> None:
        self._update_button.click()

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(UPDATED_MESSAGE)

    def expect_refused_for_missing_details(self) -> None:
        Toasts(self.page).expect_any_saying(MISSING_DETAILS)

    def expect_earning(self, earning: LoyaltyEarning) -> None:
        expect(self._amount).to_have_value(earning.amount)
        expect(self._points).to_have_value(earning.points)

    def ask_to_close(self) -> None:
        self.page.get_by_role("button", name="Esc Close").click()

    def expect_close_question(self) -> None:
        expect(Confirmation(self.page).question).to_contain_text(CLOSE_QUESTION)

    @property
    def _update_button(self) -> Locator:
        return self.page.get_by_role("button", name="F10 Update")

    @property
    def _amount(self) -> Locator:
        return self.page.get_by_role("textbox", name="Rs.", exact=True)

    @property
    def _points(self) -> Locator:
        return self.page.get_by_role("textbox", name="Point", exact=True)
