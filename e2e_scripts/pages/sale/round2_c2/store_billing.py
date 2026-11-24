"""Billing from a chosen store, and reading a store's book stock.

The bill's Store box is `txtStore<tab>`, drawn when "Ask Store?" is Yes (UI/Transaction/InverntoryTransaction/
processout.transaction.component.html:355-367; setting `txtisStore`, UtililityComponent/ControlRoom/
salebill.setting.html:1074). The garments QA company already has "Main Store" and "Scrap Store"
(test_data/stock_movement.py). A store's stock is read as "As Per Book" on a Physical Stock entry that is not
saved (tests/journeys/stock/test_stock_movement.py `_book_stock`). Part C2 owns this module.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.base_page import BasePage
from pages.sale.documents.selection_window import SelectionWindow
from pages.sale.manual.option_settings import SettingField
from pages.stock.physical_stock_page import PhysicalStockPage

ASK_STORE = SettingField("txtisStore", "Ask Store?")
STOCK_REFUSED = re.compile(r"Salable stock|negative", re.IGNORECASE)
STORE_TIMEOUT_MS = 10_000


class StoreBox(BasePage):
    @property
    def field(self) -> Locator:
        # Why an id prefix: the id carries the window number.
        return self.page.locator("[id^=txtStore]").locator("visible=true").last

    def choose(self, store: str) -> None:
        self.field.click()
        self.field.press("Control+A")
        self.field.press_sequentially(store)
        selection = SelectionWindow(self.page)
        if selection.is_shown():
            selection.choose_cell_value(store)
        else:
            self.field.press("Enter")
        expect(self.field).to_have_value(
            re.compile(re.escape(store), re.IGNORECASE), timeout=STORE_TIMEOUT_MS
        )


class StoreBillDesk(SaleBillDesk):
    """A one-line bill of 1 piece whose store is chosen right after the party."""

    store = ""

    def create_in_store(self, party: str, store: str, amount: Decimal) -> str:
        self.store = store
        return self.create(party, amount, Decimal(0))

    def open_in_store(self, party: str, store: str) -> None:
        """Opens a new bill for the party in the store and leaves it open and empty."""
        self.store = store
        self._start_for(party)

    def pick_item_only(self, item: str, quantity: Decimal) -> None:
        self._document.grid.select_product(0, item)
        self._document.grid.enter_quantity(0, quantity)

    def add_line(self, amount: Decimal) -> None:
        self._line.add(amount)

    def save_open_bill(self, party: str) -> str:
        self._open_payment_window()
        self._save_payment()
        return self._saved_number(party)

    def change_store(self, store: str) -> None:
        StoreBox(self._page).choose(store)

    def _choose_party(self, party: str) -> None:
        super()._choose_party(party)
        if self.store:
            StoreBox(self._page).choose(self.store)


def book_stock(page: Page, store: str, product: str) -> Decimal:
    """A store's stock of a product as the Physical Stock entry shows it; the entry is not saved."""
    count = PhysicalStockPage(page)
    count.start_count(store, product)
    book = count.book_quantity()
    count.abandon()
    return book
