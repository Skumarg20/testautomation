"""Stock Management > Physical Stock: count an item, save the entry, then process it from the list.

A saved entry is "Pending" and leaves the stock alone; only "Process Data" on the list sets the book
stock to the counted quantity (seen live 2026-10-08, specs/inventory.md PS-A).
"""

import contextlib
import re
from decimal import Decimal
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.inventory.item_alert import ItemAlert
from pages.stock.item_picker import StockItemPicker
from pages.stock.messages import StockMessages
from test_data.money import parse_amount

SAVED = re.compile("Record Saved Successfully", re.IGNORECASE)
PROCESSED = re.compile("Physical Stock Data Updated Successfully", re.IGNORECASE)
MANUAL_SELECTION = "Manual"
LIST_PATH = "/transaction/physicalstocklist"
CLEAR_QUESTION = "Are you sure you want to clear?"
FORM_TIMEOUT_MS = 30_000
LIST_TIMEOUT_MS = 30_000
DIFFERENCE_SETTLE_MS = 5_000
ZERO_DIFFERENCE = re.compile(r"^\s*0(\.0+)?\s*$")
BOOK = "currentToEnteredValue"
DIFFERENCE = "differenceToEnteredValue"
PRODUCT = "cus_ItemName"


class EntryStatus(Enum):
    PENDING = "Pending"
    PROCESSED = "Processed"


class PhysicalStockPage(BasePage):
    def start_count(self, store: str, product: str) -> None:
        """Opens a new entry for one store and puts one product on its first row."""
        self.open_list()
        self.page.get_by_role("button", name="Create/F2").click()
        expect(self._voucher_number).to_be_visible(timeout=FORM_TIMEOUT_MS)
        # Why ids: the header selects have no labels tied to them.
        self.page.locator("#fromStore").select_option(label=store)
        self.page.locator("#Item").select_option(label=MANUAL_SELECTION)
        StockItemPicker(self.page).choose(product)
        expect(self._first_row(PRODUCT)).to_have_text(product)

    def book_quantity(self) -> Decimal:
        """The "As Per Book" stock of the product in the chosen store."""
        return parse_amount(self._first_row(BOOK).inner_text())

    def enter_counted(self, quantity: Decimal) -> None:
        # Why an id: the row's "As Per Actual" editor has an id per row and no label.
        counted = self.page.locator("#txt-unitToEnteredValue-0")
        counted.fill(str(quantity))
        counted.press("Tab")

    def difference(self) -> Decimal:
        cell = self._first_row(DIFFERENCE)
        # Why: the app fills the difference a moment after Tab; a real zero stays zero once the wait ends.
        with contextlib.suppress(AssertionError):
            expect(cell).not_to_have_text(ZERO_DIFFERENCE, timeout=DIFFERENCE_SETTLE_MS)
        return parse_amount(cell.inner_text())

    def save(self, narration: str) -> str:
        """Saves with F10 from the narration and returns the voucher number (F10 in the grid did not save)."""
        number = self._voucher_number.input_value()
        # Why an id: the narration textarea's label is not tied to it.
        remark = self.page.locator("#txtRemark")
        remark.fill(narration)
        remark.press("F10")
        StockMessages(self.page).expect_shown(SAVED)
        return number

    def abandon(self) -> None:
        """Leaves the entry without saving it (used when the entry was only opened to read a stock)."""
        self.page.get_by_role("button", name="Back").click()
        alert = ItemAlert(self.page)
        alert.expect_asking(CLEAR_QUESTION)
        alert.answer_yes()

    def status(self, voucher: str) -> str:
        return self._list_row(voucher).locator('[col-id="status"]').inner_text().strip()

    def process(self, voucher: str) -> None:
        """Ticks the entry on the list and runs "Process Data" for it."""
        # ag-Grid draws the row tick box as an icon span without a role.
        self._list_row(voucher).locator("span.ag-icon-checkbox-unchecked").first.click()
        self.page.get_by_role("button", name="F10 Process Data").click()
        StockMessages(self.page).expect_shown(PROCESSED)

    def open_list(self) -> None:
        """By address: the sidebar entry is hidden after a save, when the app lands on this list itself."""
        self.goto(LIST_PATH)
        expect(self.page.get_by_role("button", name="Create/F2")).to_be_visible(timeout=LIST_TIMEOUT_MS)

    def _list_row(self, voucher: str) -> Locator:
        row = self.page.get_by_role("row").filter(has=self.page.get_by_text(voucher, exact=True))
        expect(row.first).to_be_visible(timeout=LIST_TIMEOUT_MS)
        return row.first

    def _first_row(self, column: str) -> Locator:
        # Why col-id: the entry grid is an ag-Grid; rows and cells carry only row-id and col-id.
        return self.page.locator(".ag-body-container").first.locator(f'[row-id="0"] [col-id="{column}"]')

    @property
    def _voucher_number(self) -> Locator:
        return self.page.locator("#txtVoucherNo")
