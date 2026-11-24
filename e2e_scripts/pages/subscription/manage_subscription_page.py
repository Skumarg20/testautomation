"""The Manage-Subscription screen: its entry from Dashboard Settings, its four tabs and its Back button."""

import re
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

SCREEN_TIMEOUT_MS = 90_000
ACTIVE_CLASS = re.compile(r"\bactive\b")


class SubscriptionTab(Enum):
    CURRENT_PLAN = "My Current Plan"
    MANAGE_PLAN = "Manage Plan"
    ADD_ON = "Add On"
    PAYMENT_HISTORY = "Payment History"


class ManageSubscriptionPage(BasePage):
    PATH = "/support/managesubscription"

    def open(self) -> None:
        self.goto(self.PATH, SCREEN_TIMEOUT_MS)
        self.expect_loaded()

    def open_from_settings(self) -> None:
        """Header Settings > Dashboard Setting > "Manage subscription and plan" > Configure."""
        self.page.get_by_role("banner").get_by_role("link", name="Settings").click()
        # Why CSS: three "Configure" buttons share one name and the row label is a bare span with no role;
        # the button's id is shared with "Get Started", so its text picks the one we need.
        self.page.locator("#btnAddonsubscription").filter(has_text="Configure").click()
        self.expect_loaded()

    def expect_loaded(self) -> None:
        expect(self.page).to_have_url(re.compile(re.escape(self.PATH)), timeout=SCREEN_TIMEOUT_MS)
        expect(self._title).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def open_tab(self, tab: SubscriptionTab) -> None:
        self._tab(tab).click()
        self.expect_tab_active(tab)

    def expect_tab_active(self, tab: SubscriptionTab) -> None:
        expect(self._tab(tab)).to_have_class(ACTIVE_CLASS)

    def go_back(self) -> None:
        self.page.get_by_role("button", name="Back").click()

    @property
    def _title(self) -> Locator:
        return self.page.get_by_role("heading", name="Manage-Subscription", level=1)

    def _tab(self, tab: SubscriptionTab) -> Locator:
        return self.page.get_by_role("tablist").get_by_role("link", name=tab.value, exact=True)
