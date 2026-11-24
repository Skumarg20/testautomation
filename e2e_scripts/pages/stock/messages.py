"""The app's toast messages on the stock screens.

These screens raise their toasts with the notifier's "material" style, so the success/warning helpers of
`pages.accounting.toasts` do not find them; they are told apart by their text instead.
"""

from re import Pattern

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

MESSAGE_TIMEOUT_MS = 50_000


class StockMessages(BasePage):
    def expect_shown(self, message: Pattern[str]) -> None:
        expect(self._toasts.filter(has_text=message).first).to_be_visible(timeout=MESSAGE_TIMEOUT_MS)

    @property
    def _toasts(self) -> Locator:
        # Why CSS: the notifier library has no role or test id (as in pages/accounting/toasts.py).
        return self.page.locator("notifier-notification")
