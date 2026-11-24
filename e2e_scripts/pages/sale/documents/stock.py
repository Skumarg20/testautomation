"""Item stock as the Master > Inventory > Item list shows it, to prove sales and returns move stock."""

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.documents.item_stock import (
    STOCK_COLUMN,
    StockReadError,
    quantities_by_product,
    stock_quantity,
)
from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.screen import DocumentScreen, exact_text

ITEM_MENU = ("Master", "Inventory Master", "Item")
REFRESH_TIMEOUT_MS = 5_000

# StockReadError is re-exported: an unreadable figure is the same error on the sale and purchase side.
__all__ = ["StockLedger", "StockMismatchError", "StockReadError", "StockSnapshot"]


@dataclass(frozen=True)
class StockSnapshot:
    before: dict[str, Decimal]


class StockLedger(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._screen = DocumentScreen(page)

    def snapshot(self, lines: tuple[ProductLine, ...]) -> StockSnapshot:
        return StockSnapshot({line.product: self.stock_of(line.product) for line in lines})

    def stock_of(self, product: str) -> Decimal:
        self._screen.open_menu(ITEM_MENU)
        cell = self._stock_cell(product)
        cell.click()
        self.page.get_by_title("Single Item Refresh").click()
        self._screen.wait_for_loader()
        expect(cell).to_be_visible(timeout=REFRESH_TIMEOUT_MS)
        return stock_quantity(product, cell.inner_text())

    def expect_sold(self, snapshot: StockSnapshot, lines: tuple[ProductLine, ...]) -> None:
        for product, quantity in _moved(lines).items():
            self._expect_stock(product, snapshot.before[product] - quantity)

    def expect_returned(self, snapshot: StockSnapshot, lines: tuple[ProductLine, ...]) -> None:
        for product, quantity in _moved(lines).items():
            self._expect_stock(product, snapshot.before[product] + quantity)

    def expect_restored(self, snapshot: StockSnapshot) -> None:
        for product, original in snapshot.before.items():
            self._expect_stock(product, original)

    def _expect_stock(self, product: str, expected: Decimal) -> None:
        actual = self.stock_of(product)
        if actual != expected:
            raise StockMismatchError(product, expected, actual)

    def _stock_cell(self, product: str) -> Locator:
        row = self.page.get_by_role("row").filter(
            has=self.page.locator('[col-id="itemcode"]').filter(has_text=exact_text(product))
        )
        return row.first.locator(f'[col-id="{STOCK_COLUMN}"]')


def _moved(lines: tuple[ProductLine, ...]) -> dict[str, Decimal]:
    """Lines of the same product move its stock by their sum."""
    return quantities_by_product((line.product, line.quantity) for line in lines)


class StockMismatchError(AssertionError):
    def __init__(self, product: str, expected: Decimal, actual: Decimal) -> None:
        super().__init__(f'Stock of "{product}": expected {expected}, found {actual}')
