"""The product grid of a purchase document: one row per line, one ag-Grid cell per field."""

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.purchase.documents import messages
from pages.purchase.documents.dates import expiry_text
from pages.purchase.documents.feedback import AppFeedback, ToastKind
from pages.purchase.documents.line_items import DiscountColumn, PurchaseLineItem
from pages.purchase.documents.selection_window import SelectionWindow
from test_data.money import parse_amount

PRODUCT = "itemLinkID"
BATCH = "batchLinkID"
EXPIRY = "expiryDate"
QUANTITY = "quantity"
FREE = "free"
RATE = "salePurchaseRate"
AMOUNT = "DisplayAmount"
PRODUCT_CODE = "cus_itemCode"
INPUT_TIMEOUT_MS = 4_000
CELL_TIMEOUT_MS = 1_000
ROW_TIMEOUT_MS = 20_000
BATCH_WINDOW_TIMEOUT_MS = 10_000
TOTAL_TIMEOUT_MS = 15_000
RATE_CHANGE_PROMPT_MS = 2_000
RATE_CHANGE_TITLE = "Update Change Rate"


@dataclass(frozen=True)
class GridProduct:
    code: str
    quantity: Decimal
    free: Decimal


class EntryGrid(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._picker = SelectionWindow(page)
        self._feedback = AppFeedback(page)

    def select_product(self, row: int, product: str) -> None:
        cell = self._cell(row, PRODUCT)
        field = cell.locator("input")
        if appears_within(field, CELL_TIMEOUT_MS):
            field.press("Enter")
        else:
            cell.click()
        if not self._picker.is_open():
            field.press("Space")
        self._choose_product(product)

    def click_product_cell(self, row: int) -> None:
        self._cell(row, PRODUCT).click()

    def expect_product_not_editing(self, row: int) -> None:
        """A document converted from another one fills its grid; the product cell is not an open editor."""
        expect(self._cell(row, PRODUCT).locator("input")).to_be_hidden(timeout=ROW_TIMEOUT_MS)

    def expect_product_empty(self, row: int) -> None:
        expect(self._cell(row, PRODUCT)).to_have_text("")

    def expect_product_shown(self, row: int) -> None:
        expect(self._cell(row, PRODUCT)).to_be_visible()

    def expect_line_carried(self, row: int, line: PurchaseLineItem) -> None:
        """A document pulled in from an earlier one shows its product, quantity and free quantity."""
        carried = self.product(row)
        assert carried == GridProduct(line.product, line.quantity, line.free)

    def type_batch(self, row: int, batch: str) -> None:
        """For a bill or challan: a new batch name is typed into the batch cell."""
        field = self.page.locator("batch-selection.ng-star-inserted input")
        if not appears_within(field, INPUT_TIMEOUT_MS):
            self._cell(row, BATCH).click()
        self._replace_text(field, batch)
        field.press("Enter")

    def pick_batch(self, row: int, batch: str) -> None:
        """For a return: an existing batch is chosen from the batch window."""
        if not self._picker.is_open():
            self._cell(row, BATCH).press("Enter")
            expect(self.page.locator("div.modal-dialog.modal-lg")).to_be_visible(
                timeout=BATCH_WINDOW_TIMEOUT_MS
            )
        self._picker.choose_cell_text(batch)

    def enter_expiry(self, row: int, serial: int | None) -> None:
        self._type_expiry(row, serial, "Tab")

    def confirm_expiry(self, row: int, serial: int | None) -> None:
        """Enter, unlike Tab, runs the expiry check (gridNavigationOnEnterKey -> validateExpiryDate,
        transactionin.component.ts:6380)."""
        self._type_expiry(row, serial, "Enter")

    def _type_expiry(self, row: int, serial: int | None, leaving_key: str) -> None:
        cell = self._cell(row, EXPIRY)
        field = cell.locator("input")
        if not appears_within(cell, CELL_TIMEOUT_MS):
            return
        if not appears_within(field, CELL_TIMEOUT_MS):
            cell.click()
        self._replace_text(field, expiry_text(serial))
        field.press(leaving_key)

    def enter_quantity(self, row: int, quantity: Decimal) -> None:
        """A quantity below one must be refused with a warning toast."""
        self.type_quantity(row, quantity)
        if quantity < 1:
            self._feedback.expect_toast_saying(ToastKind.WARNING, messages.QUANTITY_BELOW_ONE)

    def type_quantity(self, row: int, quantity: Decimal) -> None:
        # Each row's quantity editor has its own id; there is no label to find it by.
        field = self.page.locator(f"#txt-quantity-{row}")
        if not appears_within(field, INPUT_TIMEOUT_MS):
            self._cell(row, QUANTITY).click()
        field.fill(str(quantity))
        field.press("Enter")

    def enter_free(self, row: int, free: Decimal) -> None:
        cell = self._cell(row, FREE)
        if not appears_within(cell, CELL_TIMEOUT_MS):
            return
        field = cell.locator("input")
        if not appears_within(field, CELL_TIMEOUT_MS):
            cell.click()
        self._replace_text(field, str(free))
        field.press("Enter")

    def enter_rate(self, row: int, rate: Decimal) -> None:
        cell = self._cell(row, RATE)
        cell.click()
        field = cell.locator("input")
        self._replace_text(field, str(rate))
        field.press("Enter")
        self._keep_the_item_rate()

    def _keep_the_item_rate(self) -> None:
        """A rate unlike the item's asks whether to store it on the item; tests never change master data."""
        prompt = self.page.locator("ngb-modal-window").filter(has_text=RATE_CHANGE_TITLE)
        if appears_within(prompt, RATE_CHANGE_PROMPT_MS):
            prompt.get_by_role("button", name="Don't Store").click()
            expect(prompt).to_be_hidden()

    def enter_discounts(self, row: int, line: PurchaseLineItem) -> None:
        for column in DiscountColumn:
            self._enter_discount(row, column, line.discount(column))

    def product(self, row: int) -> GridProduct:
        code = self._cell(row, PRODUCT_CODE)
        expect(code).to_be_visible(timeout=ROW_TIMEOUT_MS)
        free = self._cell(row, FREE)
        shown_free = (
            Decimal(free.inner_text().strip() or 0) if appears_within(free, CELL_TIMEOUT_MS) else Decimal(0)
        )
        quantity = Decimal(self._cell(row, QUANTITY).inner_text().strip() or 0)
        return GridProduct(code.inner_text().strip(), quantity, shown_free)

    def gross_amount(self) -> Decimal:
        """The grand total row under the grid (the second ag-Grid container on the screen). It must show:
        a missing total would quietly skip the invoice value check."""
        total = self.page.locator(".ag-body-container").nth(1).locator(f'[row-id="0"] [col-id="{AMOUNT}"]')
        expect(total).to_be_visible(timeout=TOTAL_TIMEOUT_MS)
        text = total.inner_text().strip()
        return parse_amount(text) if text else Decimal(0)

    def _enter_discount(self, row: int, column: DiscountColumn, value: Decimal) -> None:
        cell = self._cell(row, column.value)
        if not appears_within(cell, CELL_TIMEOUT_MS):
            return
        cell.click()
        field = cell.locator("input")
        expect(field).to_be_visible()
        field.fill(str(value))
        field.press("Enter")

    def _choose_product(self, product: str) -> None:
        if product:
            self._picker.choose_item_code(product)
        else:
            self._picker.close_without_choosing()

    def _cell(self, row: int, column: str) -> Locator:
        # ag-Grid rows and cells carry only row-id and col-id attributes; the first container is the data.
        return self.page.locator(".ag-body-container").first.locator(f'[row-id="{row}"] [col-id="{column}"]')

    @staticmethod
    def _replace_text(field: Locator, text: str) -> None:
        if field.input_value():
            field.press("Control+A")
        field.press_sequentially(text)
