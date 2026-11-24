"""The three grids of the BOM editor: Raw Materials Consumed, By-Product Generated and Addition Cost.

From the Angular source, unverified live (billofmaterialmaster.html:58-112, billofmaterialmaster.ts:369-411):
- grid ids `#rmcproduct`, `#byproduct`, `#additional`, each with a footer grid `#<id>Foot` that reads
  "Total: n Product" / "Total: n Ledger" (setBottomData, billofmaterialmaster.ts:820-829);
- F10 moves raw -> by-product -> addition cost (hotkeys, billofmaterialmaster.ts:315-341);
- an item cell opens "Select Raw Materials Item" / "Select By-Product Item", a ledger cell opens
  "Select Addition ledger" (bom.itemselection.ts:91, 145); the cost column is `salePurchaseRate`;
- each row has a Delete action (ActionComponent).
"""

import re
from decimal import Decimal
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback
from pages.purchase.documents.selection_window import SelectionWindow
from pages.stock.messages import StockMessages
from test_data.manufacturing import Component

WINDOW_TIMEOUT_MS = 20_000


class BomGrid(Enum):
    RAW_MATERIALS = "rmcproduct"
    BY_PRODUCTS = "byproduct"
    ADDITION_COST = "additional"


class BomGrids(BasePage):
    def move_to_next_grid(self) -> None:
        self.page.keyboard.press("F10")

    def add_by_product(self, row: int, component: Component) -> None:
        SelectionWindow(self.page).choose_cell_text(component.item.product)
        self.enter_quantity(BomGrid.BY_PRODUCTS, row, component.quantity_per_set)

    def offer_item(self, product: str) -> None:
        """Clicks the item in the open item window without expecting it to close: the app may refuse it."""
        window = self._picker
        AppFeedback(self.page).wait_for_loader()
        window.get_by_role("searchbox").press_sequentially(product, delay=150)
        window.locator(".ag-cell-value").filter(has_text=_exactly(product)).first.click()

    def start_raw_row(self, row: int) -> None:
        """Opens the raw-material item window from the row's item cell (as BomMasterForm.add_raw_material)."""
        editor = self.page.locator(f"#{BomGrid.RAW_MATERIALS.value} #txt-itemLinkID-{row}")
        if not editor.is_visible():
            self._cell(BomGrid.RAW_MATERIALS, row, "itemLinkID").click()
        editor.press("Space")

    def enter_quantity(self, grid: BomGrid, row: int, quantity: Decimal) -> None:
        field = self._cell(grid, row, "quantity").locator("input")
        if not field.is_visible():
            self._cell(grid, row, "quantity").click()
        field.fill(str(quantity))
        field.press("Enter")

    def add_first_addition_ledger(self, amount: Decimal) -> None:
        """Takes the first ledger "Select Addition ledger" offers (the pack's Assembly Charges is not a
        ledger every company has), then types the cost."""
        window = self._picker
        expect(window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        window.locator(".ag-cell-value").first.click()
        AppFeedback(self.page).wait_for_loader()
        cost = self._cell(BomGrid.ADDITION_COST, 0, "salePurchaseRate").locator("input")
        cost.fill(str(amount))
        cost.press("Enter")

    def delete_row(self, grid: BomGrid, row: int) -> None:
        self._row(grid, row).get_by_role("button", name="Delete").click()

    def expect_total(self, grid: BomGrid, total: str) -> None:
        """The footer of a grid, e.g. "Total: 1 Product" or "Total: 1 Ledger"."""
        footer = self.page.locator(f"#{grid.value}Foot")
        expect(footer.get_by_text(total, exact=True)).to_be_visible()

    def expect_product_in_row(self, row: int, product: str) -> None:
        cell = self._cell(BomGrid.RAW_MATERIALS, row, "itemLinkID")
        expect(cell).to_have_text(_exactly(product))

    def expect_message(self, message: re.Pattern[str]) -> None:
        StockMessages(self.page).expect_shown(message)

    @property
    def _picker(self) -> Locator:
        # Why CSS: the item and ledger windows are Bootstrap modals with no title role (as SelectionWindow).
        return self.page.locator("div.modal-dialog.modal-lg")

    def _row(self, grid: BomGrid, row: int) -> Locator:
        # Why CSS: the editor's grids are ag-Grids; rows and cells have no names.
        return self.page.locator(f"#{grid.value}").locator(f'.ag-row[row-index="{row}"]').first

    def _cell(self, grid: BomGrid, row: int, column: str) -> Locator:
        return self._row(grid, row).locator(f'[col-id="{column}"]').first


def _exactly(text: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*{re.escape(text)}\s*$", re.IGNORECASE)
