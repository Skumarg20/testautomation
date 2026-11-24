"""Finding one item by name through the Item List search box (used to check what a company can see)."""

import re

from playwright.sync_api import Locator, Page, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from pages.inventory.item_list_page import PRODUCT, ItemListPage

FOUND_WITHIN_MS = 15_000
FILTER_TIMEOUT_MS = 30_000
KEY_DELAY_MS = 80
NAMED = re.compile(r"\S")


class ItemSearch(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._list = ItemListPage(page)

    def search(self, product: str) -> None:
        """Typed key by key on a fresh list: `fill` does not filter, and a reopened list breaks the box."""
        DashboardPage(self.page).open()
        self._list.open()
        search_box = self.page.get_by_role("searchbox", name="Search", exact=True)
        search_box.press_sequentially(product, delay=KEY_DELAY_MS)
        expect(self._other_products(product)).to_have_count(0, timeout=FILTER_TIMEOUT_MS)

    def expect_found(self, product: str) -> None:
        self._list.expect_listed(product)

    def expect_not_found(self, product: str) -> None:
        self._list.expect_not_listed(product)

    def delete_if_found(self, product: str) -> None:
        """Teardown helper: the item may already be gone when its test deleted it or never saved it."""
        if appears_within(self.page.get_by_role("gridcell", name=product, exact=True), FOUND_WITHIN_MS):
            self._list.delete(product)

    def _other_products(self, product: str) -> Locator:
        """Named product cells that do not match the search; the grid also renders empty filler cells."""
        # Why col-id: the grid is an ag-Grid; its cells are told apart only by col-id.
        product_cells = self.page.get_by_role("gridcell").and_(self.page.locator(f'[col-id="{PRODUCT}"]'))
        return product_cells.filter(has_text=NAMED).filter(has_not_text=product)
