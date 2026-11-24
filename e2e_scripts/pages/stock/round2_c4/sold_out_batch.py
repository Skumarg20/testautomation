"""Picking a batch that has no stock left on a sale bill line.

The batch window hides batches with no stock until "ShowAll Batch" (F7), processinbatch.component.ts:575-597
and :991-993. A pick is then judged in `onRowDoubleClick` (processinbatch.component.ts:1069-1076): with "Stock
Negative allowed" = No a batch with `OpeningQuantity <= 0` is refused with "Stock not available. Select
another
batch!" (global.ts:19473, `AlertMsg.Batchstock`) and the window stays open; with Yes or Item wise the batch is
taken and the quantity rules of `applyStockNegativeSetting` decide
(processout.transaction.component.ts:12713).
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.item_grid import BATCH as BATCH_COLUMN
from pages.sale.documents.screen import exact_text
from pages.sale.manual.pharma_bill import ITEM, PharmaBill
from pages.stock.search_typing import type_search

STOCK_NOT_AVAILABLE = "Stock not available. Select another batch!"
SHOW_ALL_BATCHES_KEY = "F7"
WINDOW_TIMEOUT_MS = 20_000
LIST_TIMEOUT_MS = 30_000


class SoldOutBatchLine(BasePage):
    """The first line of an open sale bill, used to try a batch with no stock."""

    def __init__(self, bill: PharmaBill) -> None:
        super().__init__(bill.page)
        self._bill = bill

    def open_all_batches(self, row: int) -> None:
        """Picks the item on `row`, opens its batch window and shows the batches with no stock too."""
        document = self._bill.document
        document.grid.select_product(row, ITEM)
        if not document.selection.is_shown():
            document.grid.cell(row, BATCH_COLUMN).press("Enter")
        expect(self.page.locator('[col-id="batchName"]').first).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        self.page.keyboard.press(SHOW_ALL_BATCHES_KEY)
        document.screen.wait_for_loader()

    def take(self, batch: str) -> None:
        """Picks the batch and waits until the window has accepted it and closed."""
        self._bill.document.selection.choose_cell_value(batch)

    def try_take(self, batch: str) -> None:
        """Clicks the batch and does not wait for the window to close: a refused pick leaves it open."""
        type_search(self._window.get_by_role("searchbox"), batch)
        row = self._window.locator(".ag-cell-value").filter(has_text=exact_text(batch))
        expect(row.first).to_be_visible(timeout=LIST_TIMEOUT_MS)
        row.first.click()

    def expect_window_still_open(self) -> None:
        expect(self._window).to_be_visible()

    def close_window(self) -> None:
        self._bill.document.selection.close()

    @property
    def _window(self) -> Locator:
        # Why CSS: the batch window is a Bootstrap modal with no role or test id (SelectionWindow._window).
        return self.page.locator("div.modal-dialog.modal-lg")
