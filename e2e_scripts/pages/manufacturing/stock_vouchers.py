"""Material Issue, Material Received, One to Many and Many to One: the stock vouchers of manufacturing.

All four are the app's common transaction screen (list with "Create/F2", party picker, item grid), so they
reuse the purchase document widgets. None of them could be opened live on 2026-10-12: with the Control Room
switches off, `/sale/matissue`, `/purchase/matrecieve`, `/purchase/onetomany` and `/purchase/manytoone`
redirect to the dashboard. Locators follow the Angular source and are unverified live.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.manufacturing.menu import ManufacturingMenu, ManufacturingScreen
from pages.purchase.documents.document_list import DocumentList
from pages.purchase.documents.entry_grid import EntryGrid
from pages.purchase.documents.feedback import AppFeedback
from pages.purchase.documents.fields import labelled_input
from pages.purchase.documents.selection_window import SelectionWindow
from pages.stock.messages import StockMessages
from test_data.manufacturing import PRODUCTION_DEPARTMENT, ConversionDirection

WINDOW_TIMEOUT_MS = 20_000
ISSUE_SAVED = re.compile(r"Bill of Material saved successfully!")
SAVED = re.compile(r"Saved successfully!")


class StockVoucherForm(BasePage):
    screen: ManufacturingScreen
    saved_message: re.Pattern[str] = SAVED
    number_label = "Invoice No."

    def open_new(self) -> None:
        self.start_new()
        SelectionWindow(self.page).choose_cell_text(PRODUCTION_DEPARTMENT)

    def start_new(self) -> None:
        """Create/F2: the screen opens with its party window up."""
        ManufacturingMenu(self.page).open_screen(self.screen)
        DocumentList(self.page).create()

    def add_line(self, row: int, product: str, quantity: Decimal) -> None:
        grid = EntryGrid(self.page)
        grid.select_product(row, product)
        grid.enter_quantity(row, quantity)

    def number(self) -> str:
        """The voucher number the screen proposes; read before saving, for the teardown to delete it."""
        return labelled_input(self.page, self.number_label).input_value()

    def save(self) -> None:
        self.page.get_by_role("button", name="Save").click()
        AppFeedback(self.page).confirm_if_asked()

    def expect_saved(self) -> None:
        StockMessages(self.page).expect_shown(self.saved_message)

    def delete(self, number: str) -> None:
        ManufacturingMenu(self.page).open_screen(self.screen)
        DocumentList(self.page).delete(number)


class MaterialIssue(StockVoucherForm):
    """A sale-type voucher: the raw materials leave the main store (pack MF-14)."""

    screen = ManufacturingScreen.MATERIAL_ISSUE
    saved_message = ISSUE_SAVED
    # A sale-type screen: its number field is "Bill No." (billofmaterialissue.factory.ts:37).
    number_label = "Bill No."


class MaterialReceive(StockVoucherForm):
    """A purchase-type voucher: the finished item comes in; its raw materials are only listed (MF-18)."""

    screen = ManufacturingScreen.MATERIAL_RECEIVE


class OneToMany(StockVoucherForm):
    screen = ManufacturingScreen.ONE_TO_MANY

    def choose_big_item(self, product: str) -> None:
        """Row 0 first asks for the item converted from or into (transactionin.component.ts:6835)."""
        EntryGrid(self.page).click_product_cell(0)
        SelectionWindow(self.page).choose_cell_text(product)


class ManyToOne(OneToMany):
    screen = ManufacturingScreen.MANY_TO_ONE


CONVERSION_VOUCHERS: dict[ConversionDirection, type[OneToMany]] = {
    ConversionDirection.ONE_TO_MANY: OneToMany,
    ConversionDirection.MANY_TO_ONE: ManyToOne,
}


class RawMaterialsConsumedWindow(BasePage):
    """The "Raw Materials Consumed" window a receive opens (billofmaterialdetails.ts:16-50)."""

    def expect_quantity(self, product: str, quantity: Decimal) -> None:
        row = self._window.get_by_role("row").filter(has=self.page.get_by_text(product, exact=True))
        # Why col-id: the window's grid cells have no names; the quantity column is "quantity".
        expect(row.locator('[col-id="quantity"]')).to_have_text(re.compile(rf"^{quantity}(\.0+)?$"))

    def accept(self) -> None:
        self._window.get_by_role("button", name="Ok").click()
        expect(self._window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    def expect_refused(self, message: re.Pattern[str]) -> None:
        self._window.get_by_role("button", name="Ok").click()
        StockMessages(self.page).expect_shown(message)
        expect(self._window).to_be_visible()

    @property
    def _window(self) -> Locator:
        heading = self.page.get_by_role("heading", name="Raw Materials Consumed")
        # Why CSS: the window is a plain div overlay without a dialog role; its heading is the handle.
        return self.page.locator("div.frameModal").filter(has=heading)


class StockUpdateWindow(BasePage):
    """The "Stock Update" / "Less Stock" window a conversion save shows (KB `#25e8dd21`, `#c036bd72`)."""

    def accept(self) -> None:
        self.page.get_by_role("button", name=re.compile(r"^ok$", re.IGNORECASE)).click()


class SavedVoucher:
    """A saved voucher a test may delete itself (MF-26); the fixture deletes it only if the test did not."""

    def __init__(self, voucher: StockVoucherForm, number: str) -> None:
        self.voucher = voucher
        self.number = number
        self._deleted = False

    def delete(self) -> None:
        self.voucher.delete(self.number)
        self._deleted = True

    def delete_if_left(self) -> None:
        if not self._deleted:
            self.delete()
