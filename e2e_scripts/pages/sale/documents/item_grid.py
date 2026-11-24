"""The item grid of a sale document. Cells are found by the `col-id` the app gives each column."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.document_requests import parse_decimal, plain
from pages.sale.documents.screen import is_shown_within
from pages.sale.documents.selection_window import SelectionWindow

PRODUCT = "itemLinkID"
BATCH = "batchLinkID"
QUANTITY = "unitToEnteredValue"
PRICE = "salePurchaseRate"
AMOUNT = "DisplayAmount"
FIRST_DISCOUNT = "discount1"
SECOND_DISCOUNT = "discount2"
FIRST_VOLUME_DISCOUNT = "volumediscount"
SECOND_VOLUME_DISCOUNT = "volumediscount2"
CELL_WAIT_MS = 1_000
CELL_TIMEOUT_MS = 5_000
SCROLL_TO_RIGHT_END = "viewports => viewports.forEach(el => { el.scrollLeft = el.scrollWidth; })"
SCROLL_TO_LEFT_END = "viewports => viewports.forEach(el => { el.scrollLeft = 0; })"
BATCH_LIST_TIMEOUT_MS = 5_000


class DocumentItemGrid(BasePage):
    def cell(self, row: int, column: str) -> Locator:
        # ag-Grid renders the editable rows in the first body container; the totals row is in the second.
        body = self.page.locator('[ref="eBodyContainer"]').first
        return body.locator(f'[row-id="{row}"] [col-id="{column}"]')

    def select_product(self, row: int, product: str) -> None:
        cell = self.cell(row, PRODUCT)
        editor = cell.locator("input")
        if is_shown_within(editor, CELL_WAIT_MS):
            editor.press("Enter")
        else:
            cell.click()
        if not self._selection.is_shown():
            editor.press("Space")
        self._selection.choose_in_column("itemcode", product)

    def choose_batch(self, row: int, batch: str) -> None:
        """A batch the case names must be chosen; only a line without a batch may find no batch cell."""
        if not self._selection.is_shown():
            cell = self.cell(row, BATCH)
            if not is_shown_within(cell, CELL_WAIT_MS):
                if not batch:
                    return
                expect(cell).to_be_visible(timeout=CELL_TIMEOUT_MS)
            cell.press("Enter")
        expect(self.page.locator('[col-id="batchName"]').first).to_be_visible(timeout=BATCH_LIST_TIMEOUT_MS)
        self._selection.choose_cell_value(batch)

    def enter_quantity(self, row: int, quantity: Decimal) -> None:
        self.cell(row, QUANTITY).click()
        editor = self.cell(row, QUANTITY).locator("input")
        editor.press_sequentially(plain(quantity))
        editor.press("Enter")

    def displayed_price(self, row: int) -> Decimal:
        return parse_decimal(self.cell(row, PRICE).inner_text())

    def type_price(self, row: int, price: Decimal) -> None:
        self.cell(row, PRICE).click()
        self.cell(row, PRICE).locator("input").press_sequentially(plain(price))

    def confirm_low_price(self, row: int) -> None:
        self.cell(row, PRICE).locator("input").press("Enter")

    def finish_price(self, row: int) -> None:
        self.cell(row, PRICE).locator("input").press("Tab")
        self.cell(row, PRICE).press("Enter")

    def accept_default_price(self, row: int) -> None:
        self.cell(row, PRICE).click()
        self.cell(row, PRICE).locator("input").press("Tab")
        self.cell(row, PRICE).press("Enter")

    def enter_discount(self, row: int, column: str, value: Decimal) -> None:
        """A zero discount is left alone; any other must reach its cell, or the scenario would not run."""
        if value == 0:
            return
        cell = self.cell(row, column)
        if is_shown_within(cell, CELL_WAIT_MS):
            self._type_into(cell, value)
            return
        self._scroll_grid(SCROLL_TO_RIGHT_END)
        expect(cell).to_be_visible(timeout=CELL_TIMEOUT_MS)
        self._type_into(cell, value)
        self._scroll_grid(SCROLL_TO_LEFT_END)

    def amount(self, row: int) -> Decimal:
        cell = self.cell(row, AMOUNT)
        expect(cell).to_have_text(re.compile(r"\d"))
        return parse_decimal(cell.inner_text())

    def quantity_in_grid(self, row: int) -> Decimal:
        return parse_decimal(self.cell(row, QUANTITY).inner_text())

    def expect_product_shown(self, row: int) -> None:
        expect(self.cell(row, PRODUCT)).to_be_visible()

    def open_first_product_cell(self) -> None:
        self.cell(0, PRODUCT).click()

    def totals_amount(self) -> Locator:
        return (
            self.page.locator('[ref="eBodyContainer"]')
            .nth(1)
            .locator('[row-id="0"] [col-id="DisplayAmount"]')
        )

    def _scroll_grid(self, script: str) -> None:
        """ag-Grid draws only the columns in view, and the discount columns sit far to the right."""
        self.page.locator(".ag-body-viewport").evaluate_all(script)

    @staticmethod
    def _type_into(cell: Locator, value: Decimal) -> None:
        cell.click()
        editor = cell.locator("input")
        editor.fill(plain(value))
        editor.press("Enter")

    @property
    def _selection(self) -> SelectionWindow:
        return SelectionWindow(self.page)
