"""A voucher or ledger list: search box, date range filter and opening a row."""

from playwright.sync_api import Locator, expect

from pages.accounting.loader import Loader
from pages.base_page import BasePage

THIS_WEEK = "This Week"
ROW_TIMEOUT_MS = 30_000


class ListScreen(BasePage):
    def search(self, text: str) -> None:
        box = self._search_box
        box.press("Control+A")
        box.press("Backspace")
        box.press_sequentially(text)
        Loader(self.page).wait_until_idle()

    def filter_to_this_week(self) -> None:
        # Why CSS: the range filter is a dropdown button with classes only.
        self.page.locator("button.default-btn.dropdown-toggle").click()
        # Why CSS: the range options are anchors without href, so they have no link role.
        self.page.locator(".dropdown-menu.show").get_by_text(THIS_WEEK, exact=True).click()
        Loader(self.page).wait_until_idle()

    def open_row(self, unique_text: str) -> None:
        self.page.get_by_text(unique_text, exact=True).first.dblclick()
        Loader(self.page).wait_until_idle()

    def open_only_row(self, cell_text: str) -> None:
        """Opens the row with a cell reading exactly `cell_text`, after checking that no other row has one."""
        cell = self.page.get_by_role("gridcell", name=cell_text, exact=True)
        expect(cell).to_have_count(1, timeout=ROW_TIMEOUT_MS)
        cell.dblclick()
        Loader(self.page).wait_until_idle()

    @property
    def _search_box(self) -> Locator:
        # Why ids and a class: list pages use a different search input id per screen.
        return self.page.locator("#SearchBox, #searchItems, .searchFilterBox input[name='SearchBox']").first
