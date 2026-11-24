"""A manual sale return of a batch that has no stock left: its batch is picked after "ShowAll Batch".

The batch window hides zero-stock batches until F7 (processinbatch.component.ts:575-597, :991-993), so the
ordinary pick cannot reach the batch of a return made when nothing of it is left.
"""

from playwright.sync_api import expect

from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.item_grid import BATCH
from pages.sale.documents.returns import SaleReturn

WINDOW_TIMEOUT_MS = 20_000
SHOW_ALL_BATCHES_KEY = "F7"


class ZeroStockReturn(SaleReturn):
    def choose_batch(self, row: int, line: ProductLine) -> None:
        if not self.selection.is_shown():
            self.grid.cell(row, BATCH).press("Enter")
        expect(self.page.locator('[col-id="batchName"]').first).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        self.page.keyboard.press(SHOW_ALL_BATCHES_KEY)
        self.screen.wait_for_loader()
        self.selection.choose_cell_value(line.batch)
