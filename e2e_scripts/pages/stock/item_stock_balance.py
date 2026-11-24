"""An item's stock in the main store, read from the Item List after the item's balance is refreshed.

The Item List shows a cached balance: an opening stock or a processed physical stock shows only after
"Single Item Refresh" (KB "Refresh Item Stock Balance", scenario IN-28). The list is filtered on the main
store, so the figure is the main-store stock.
"""

import re
from contextlib import suppress
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.inventory.item_list_page import PRODUCT, STOCK, ItemListPage
from pages.stock.messages import StockMessages
from pages.stock.search_typing import type_search
from test_data.money import parse_amount

REDRAW_TIMEOUT_MS = 5_000
REFRESHED = re.compile("Refreshed Successfully", re.IGNORECASE)


class ItemStockBalance(BasePage):
    def main_store_stock(self, product: str) -> Decimal:
        ItemListPage(self.page).open()
        # The grid draws only the rows near the screen, so the item is searched for first.
        type_search(self.page.get_by_role("searchbox", name="Search", exact=True), product)
        cell = self._stock_cell(product)
        cached = cell.inner_text()
        cell.click()
        self.page.get_by_title("Single Item Refresh").click()
        StockMessages(self.page).expect_shown(REFRESHED)
        self._wait_for_redraw(cell, cached)
        return parse_amount(cell.inner_text())

    @staticmethod
    def _wait_for_redraw(cell: Locator, cached: str) -> None:
        """The refreshed balance is drawn a moment after the toast; an unchanged balance never redraws."""
        with suppress(AssertionError):
            expect(cell).not_to_have_text(cached, timeout=REDRAW_TIMEOUT_MS)

    def _stock_cell(self, product: str) -> Locator:
        # Why col-id: the Item List is an ag-Grid whose cells are told apart only by col-id.
        name_cell = self.page.get_by_role("gridcell").and_(self.page.locator(f'[col-id="{PRODUCT}"]'))
        row = self.page.get_by_role("row").filter(has=name_cell.get_by_text(product, exact=True))
        return row.locator(f'[col-id="{STOCK}"]')
