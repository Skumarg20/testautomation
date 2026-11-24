"""Stock Management > Stock Transfer: move a quantity of one product from one store to another."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.stock.item_picker import StockItemPicker
from pages.stock.messages import StockMessages
from pages.stock.stock_menu import StockMenu, StockScreen

TRANSFERRED = re.compile("Store Transferred Successfully", re.IGNORECASE)
MANUAL_STOCK_TYPE = "Manual"
FORM_TIMEOUT_MS = 30_000
HEADER_FIELDS_TO_PICKER = 4
PICKER_LOOKUP_MS = 1_500


class StoreTransfer:
    """What to move: a quantity of one product, from one store to another."""

    def __init__(self, product: str, quantity: Decimal, stores: tuple[str, str]) -> None:
        self.product = product
        self.quantity = quantity
        self.from_store, self.to_store = stores


class StockTransferPage(BasePage):
    def transfer(self, move: StoreTransfer) -> None:
        self._open_new()
        self._choose_stores(move)
        self._open_item_picker()
        StockItemPicker(self.page).choose(move.product)
        self._enter_quantity(move.quantity)
        self.page.keyboard.press("End")
        StockMessages(self.page).expect_shown(TRANSFERRED)

    def _open_new(self) -> None:
        StockMenu(self.page).open_stock_screen(StockScreen.TRANSFER)
        self.page.get_by_role("button", name="Create/F2").click()
        expect(self._select("stockType")).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def _choose_stores(self, move: StoreTransfer) -> None:
        self._select("fromStore").select_option(label=move.from_store)
        self._select("toStore").select_option(label=move.to_store)
        self._select("stockType").select_option(label=MANUAL_STOCK_TYPE)

    def _open_item_picker(self) -> None:
        """Manual stock type: Enter from the stock type moves through the barcode cell to the picker."""
        self._select("stockType").focus()
        picker = StockItemPicker(self.page)
        for _ in range(HEADER_FIELDS_TO_PICKER):
            self.page.keyboard.press("Enter")
            if picker.opens_within(PICKER_LOOKUP_MS):
                return
        picker.expect_open()

    def _enter_quantity(self, quantity: Decimal) -> None:
        # Why an id: each row's quantity editor has its own id and no label.
        field = self.page.locator("#txt-quantity-0")
        field.fill(str(quantity))
        field.press("Enter")

    def _select(self, control: str) -> Locator:
        # Why formcontrolname: the selects have numbered ids and no labels tied to them.
        return self.page.locator(f"select[formcontrolname='{control}']")
