"""Create Item with a typed barcode, and that barcode shown again by Edit/F3 (Master > Inventory > Item)."""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_alert import ItemAlert
from pages.inventory.item_list_page import ItemListPage
from pages.stock.opening_stock import OpeningStockWindow
from test_data.models import ItemMasterSpec

FORM_TIMEOUT_MS = 30_000


class BarcodedItem(BasePage):
    def create(self, item: ItemMasterSpec, barcode: str) -> None:
        """Saves the item with this barcode and declines the opening-stock offer."""
        form = self._submit(item, barcode)
        form.expect_saved()
        form.decline_opening_stock()

    def create_with_opening(self, item: ItemMasterSpec, barcode: str, quantity: Decimal) -> None:
        """Saves the item with this barcode and the quantity as main-store opening stock."""
        form = self._submit(item, barcode)
        form.expect_saved()
        form.expect_opening_stock_offered()
        # Not ItemAlert.answer_yes: it waits for the alert box to close, and the Opening window that
        # follows is drawn with the same box classes (as in pages/stock/opening_stock.py).
        ItemAlert(self.page).question.locator("#btnYes").click()
        opening = OpeningStockWindow(self.page)
        opening.enter(quantity)
        opening.expect_saved()

    def try_create(self, item: ItemMasterSpec, barcode: str) -> None:
        """Fills and saves the form without expecting the outcome; for saves the app may refuse."""
        self._submit(item, barcode)

    def expect_barcode_on_edit(self, product: str, barcode: str) -> None:
        item_list = ItemListPage(self.page)
        item_list.open()
        item_list.edit(product)
        CreateItemPage(self.page).expect_editing(product)
        expect(self._barcode).to_have_value(barcode, timeout=FORM_TIMEOUT_MS)

    def expect_not_saved(self, product: str) -> None:
        DashboardPage(self.page).open()  # leaves the form and any refusal dialog over it
        item_list = ItemListPage(self.page)
        item_list.open()
        item_list.expect_not_listed(product)

    def _submit(self, item: ItemMasterSpec, barcode: str) -> CreateItemPage:
        form = CreateItemPage(self.page)
        form.open()
        # Typed key by key: fill() left the uppercase-transform field empty on the saved item (2026-10-15).
        self._barcode.press_sequentially(barcode)
        form.fill(item)
        form.save()
        return form

    @property
    def _barcode(self) -> Locator:
        # Why an id: the Barcode label is not tied to its input (same as the other Create Item fields).
        return self.page.locator("#txtBarcode")
