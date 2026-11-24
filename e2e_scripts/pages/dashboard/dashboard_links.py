"""Where the dashboard leads: the report behind each summary card, the Shortcut Keys panel and Alt+H home."""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.shortcut import press_until_visible
from pages.dashboard.figures import DashboardFigures, SummaryCard

REPORT_TIMEOUT_MS = 60_000
HOME_SHORTCUT = "Alt+H"
CARD_REPORTS: dict[SummaryCard, tuple[str, str]] = {
    SummaryCard.NET_SALE: ("/report/register/sale", "Sale Register"),
    SummaryCard.NET_PURCHASE: ("/report/register/purchase", "Purchase Register"),
    # Since V 4.3.599.b the card opens the new Gross Profit report (agreed with the user 2026-10-14).
    SummaryCard.GROSS_PROFIT: ("/report/grossreport/gp-default", "Gross Profit"),
}


class DashboardLinks(BasePage):
    def open_card_report(self, card: SummaryCard) -> None:
        DashboardFigures(self.page).open_card_report(card)

    def expect_card_report_open(self, card: SummaryCard) -> None:
        path, title = CARD_REPORTS[card]
        expect(self.page).to_have_url(re.compile(re.escape(path) + "$"), timeout=REPORT_TIMEOUT_MS)
        report_title = self.page.get_by_role("heading", name=re.compile(rf"^{re.escape(title)}"), level=1)
        expect(report_title).to_be_visible(timeout=REPORT_TIMEOUT_MS)

    def open_shortcut_keys(self) -> None:
        self.page.get_by_role("banner").get_by_role("link", name="Shortcut", exact=True).click()

    def expect_shortcut_listed(self, action: str, keys: str) -> None:
        expect(self._shortcut_heading).to_be_visible()
        expect(self.page.get_by_text(action, exact=True)).to_be_visible()
        expect(self.page.get_by_text(keys, exact=True).first).to_be_visible()

    def go_home_by_shortcut(self) -> None:
        press_until_visible(self.page, HOME_SHORTCUT, self._dashboard_title)

    def expect_on_dashboard(self) -> None:
        expect(self.page).to_have_url(re.compile(r"/dashboard$"), timeout=REPORT_TIMEOUT_MS)
        expect(self._dashboard_title).to_be_visible(timeout=REPORT_TIMEOUT_MS)

    @property
    def _shortcut_heading(self) -> Locator:
        return self.page.get_by_role("heading", name="SHORTCUT KEYS", exact=True)

    @property
    def _dashboard_title(self) -> Locator:
        return self.page.get_by_role("main").get_by_role("button", name="Refresh Dashboard")
