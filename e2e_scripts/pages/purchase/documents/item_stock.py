"""Current stock of an item, read from the item master after a refresh, and the checks on how it moved."""

import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback, ToastKind
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.purchase.documents.navigation import ModuleMenu

REFRESH_TOAST_TIMEOUT_MS = 50_000
CELL_TIMEOUT_MS = 5_000
EMPTY_STOCK = "0:0"
# The item list's "Stock" column (the multi-unit "multiunitdetails" column until V 4.3.599).
STOCK_COLUMN = "Opening"


class StockReadError(ValueError):
    def __init__(self, item_code: str, text: str) -> None:
        super().__init__(f'Stock of item "{item_code}" reads "{text}", which is not a plain number')


class StockMismatchError(AssertionError):
    def __init__(self, item_code: str, expected: Decimal, found: Decimal) -> None:
        super().__init__(f'Stock of item "{item_code}": expected {expected}, found {found}')


class ItemStock(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._menu = ModuleMenu(page)
        self._feedback = AppFeedback(page)

    def current(self, item_code: str) -> Decimal:
        self._menu.open_item_master()
        cell = self._stock_cell(item_code)
        cell.click()
        self.page.get_by_title("Single Item Refresh").click()
        self._feedback.toast_appears(ToastKind.SUCCESS, REFRESH_TOAST_TIMEOUT_MS)
        self._feedback.wait_for_loader()
        expect(cell).to_be_visible(timeout=CELL_TIMEOUT_MS)
        return stock_quantity(item_code, cell.inner_text())

    def snapshot(self, lines: tuple[PurchaseLineItem, ...]) -> dict[str, Decimal]:
        """Stock of every product named in the lines, by item code."""
        return {line.product: self.current(line.product) for line in lines if line.product}

    def expect_received(self, lines: tuple[PurchaseLineItem, ...], before: dict[str, Decimal]) -> None:
        """Free goods count as received; lines of the same product are added up first."""
        received = quantities_by_product((line.product, line.quantity + line.free) for line in lines)
        for item_code, quantity in received.items():
            self.expect_increase(item_code, before[item_code], quantity)

    def expect_back_to(self, before: dict[str, Decimal]) -> None:
        for item_code, original in before.items():
            self.expect_restored(item_code, original)

    def expect_increase(self, item_code: str, before: Decimal, received: Decimal) -> None:
        self._expect(item_code, before + received)

    def expect_decrease(self, item_code: str, before: Decimal, returned: Decimal) -> None:
        self._expect(item_code, before - returned)

    def expect_restored(self, item_code: str, original: Decimal) -> None:
        self._expect(item_code, original)

    def _expect(self, item_code: str, expected: Decimal) -> None:
        found = self.current(item_code)
        if found != expected:
            raise StockMismatchError(item_code, expected, found)

    def _stock_cell(self, item_code: str) -> Locator:
        # The item master is an ag-Grid: rows by item-code cell, stock in the Stock cell.
        code = re.compile(rf"^\s*{re.escape(item_code)}\s*$", re.IGNORECASE)
        row = self.page.get_by_role("row").filter(
            has=self.page.locator('[col-id="itemcode"]').filter(has_text=code)
        )
        return row.locator(f'[col-id="{STOCK_COLUMN}"]').first


def quantities_by_product(quantities: Iterable[tuple[str, Decimal]]) -> dict[str, Decimal]:
    """Adds up (product, quantity) pairs per product; a pair without a product is left out."""
    totals: dict[str, Decimal] = {}
    for product, quantity in quantities:
        if product:
            totals[product] = totals.get(product, Decimal(0)) + quantity
    return totals


def stock_quantity(item_code: str, text: str) -> Decimal:
    """The item list shows 0:0 for no stock; any other figure must be a plain number."""
    shown = text.strip()
    try:
        return Decimal(0) if shown == EMPTY_STOCK else Decimal(shown)
    except InvalidOperation:
        raise StockReadError(item_code, shown) from None
