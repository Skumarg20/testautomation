"""The "Opening" window the item master offers after an item is saved (Yes on "add item Opening?")."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_alert import ItemAlert
from pages.stock.messages import StockMessages
from test_data.models import ItemMasterSpec

STOCK_UPDATED = re.compile("Stock Updated Successfully", re.IGNORECASE)
WINDOW_TIMEOUT_MS = 30_000


class OpeningStockWindow(BasePage):
    def enter(self, quantity: Decimal) -> None:
        # Why ids: the inputs and buttons of this window have no labels tied to them, and both buttons
        # carry aria-label="Close". The form itself has no size (its content is an overlay), so the
        # quantity input is what becomes visible.
        quantity_field = self._form.locator("#opening")
        expect(quantity_field).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        quantity_field.fill(str(quantity))
        self._form.locator("#btnSave").click()

    def expect_saved(self) -> None:
        StockMessages(self.page).expect_shown(STOCK_UPDATED)

    @property
    def _form(self) -> Locator:
        return self.page.locator("#itemOpening")


def create_item_with_opening(page: Page, item: ItemMasterSpec, quantity: Decimal) -> None:
    """Creates the item and answers Yes to "add item Opening?" with the given main-store quantity."""
    form = CreateItemPage(page)
    form.open()
    form.fill(item)
    form.save()
    form.expect_saved()
    form.expect_opening_stock_offered()
    # Not ItemAlert.answer_yes: it waits for the alert box to close, and the Opening window that
    # follows is drawn with the same box classes.
    ItemAlert(page).question.locator("#btnYes").click()
    opening = OpeningStockWindow(page)
    opening.enter(quantity)
    opening.expect_saved()
