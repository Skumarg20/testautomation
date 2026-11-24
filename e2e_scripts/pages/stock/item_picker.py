"""The "Select Item" window that stock documents open to choose a product by its name."""

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within, disappears_within
from pages.base_page import BasePage
from pages.stock.search_typing import type_search

OPEN_TIMEOUT_MS = 20_000
CLOSE_LOOKUP_MS = 5_000


class StockItemPicker(BasePage):
    def expect_open(self) -> None:
        expect(self._window).to_be_visible(timeout=OPEN_TIMEOUT_MS)

    def opens_within(self, timeout_ms: int) -> bool:
        return appears_within(self._window, timeout_ms)

    def choose(self, product: str) -> None:
        """Searches the name and clicks its row; where a click only selects the row, Enter takes it."""
        self.expect_open()
        window = self._window
        type_search(window.get_by_role("searchbox", name="Search"), product)
        window.get_by_role("gridcell", name=product, exact=True).click()
        if not disappears_within(window, CLOSE_LOOKUP_MS):
            self.page.keyboard.press("Enter")
        expect(window).to_be_hidden(timeout=OPEN_TIMEOUT_MS)

    def close(self) -> None:
        self._window.get_by_role("button", name="Esc Close").click()
        expect(self._window).to_be_hidden()

    @property
    def _window(self) -> Locator:
        # The picker is an ngb modal; older copies stay in the DOM, so the newest one is used.
        return self.page.get_by_role("dialog").filter(has_text="Select Item").last
