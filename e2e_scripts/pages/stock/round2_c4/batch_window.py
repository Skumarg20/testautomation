"""The batch window of a sale bill line, opened to look at it and to press keys that create or edit batches.

`ProcessInBatchComponent.hotkeys` (processinbatch.component.ts:951-1000): F2 only calls `preventDefault`
(the item window's "create" key does nothing here) and F3 edits the highlighted batch (`editbatch`). No key of
the window adds a batch, so a sale cannot create one.
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.item_grid import BATCH as BATCH_COLUMN
from pages.sale.manual.pharma_bill import ITEM, PharmaBill

WINDOW_TIMEOUT_MS = 20_000


class BatchWindowOfBill(BasePage):
    def __init__(self, bill: PharmaBill) -> None:
        super().__init__(bill.page)
        self._bill = bill

    def open(self, row: int, product: str = ITEM) -> None:
        document = self._bill.document
        document.grid.select_product(row, product)
        if not document.selection.is_shown():
            document.grid.cell(row, BATCH_COLUMN).press("Enter")
        expect(self.page.locator('[col-id="batchName"]').first).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def listed_batches(self) -> int:
        return self._rows.count()

    def open_windows(self) -> int:
        # Why CSS: ng-bootstrap modals have no role-based count that excludes hidden stacked ones.
        return self.page.locator("ngb-modal-window:not([aria-hidden='true'])").count()

    def listed_names(self) -> list[str]:
        """The batch names in the order the window lists them, blank rows left out."""
        names = self.page.locator('div.modal-dialog.modal-lg [col-id="batchName"]').all_inner_texts()
        return [name.strip() for name in names if name.strip() and name.strip().lower() != "batch name"]

    def press(self, key: str) -> None:
        self.page.keyboard.press(key)

    def close(self) -> None:
        self._bill.document.selection.close()

    @property
    def _rows(self) -> Locator:
        window = self.page.locator("div.modal-dialog.modal-lg")
        return window.locator(".ag-center-cols-container .ag-row")
