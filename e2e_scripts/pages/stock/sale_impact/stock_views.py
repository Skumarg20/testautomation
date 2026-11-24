"""One item and batch read in the three places the stock sheet names: Item List, Batch List, Item Register."""

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Page

from pages.base_page import BasePage
from pages.sale.documents.stock import StockLedger
from pages.stock.sale_impact.batch_list import BatchList
from pages.stock.sale_impact.documents import PRODUCT
from pages.stock.sale_impact.item_register import ItemRegister


@dataclass(frozen=True)
class StockReading:
    item_list: Decimal
    batch_list: Decimal
    item_register: Decimal

    def moved_by(self, change: Decimal) -> "StockReading":
        return StockReading(self.item_list + change, self.batch_list + change, self.item_register + change)


class StockViewMismatchError(AssertionError):
    def __init__(self, view: str, expected: Decimal, found: Decimal) -> None:
        super().__init__(f"{view}: expected {expected}, found {found}")


class StockViews(BasePage):
    """The stock of `product` and of its `batch`, as the three screens show it."""

    def __init__(self, page: Page, product: str, batch: str) -> None:
        super().__init__(page)
        self._product = product
        self._batch = batch
        self._item_list = StockLedger(page)
        self._batch_list = BatchList(page)
        self._register = ItemRegister(page)

    def read(self) -> StockReading:
        return StockReading(
            item_list=self._item_list.stock_of(self._product),
            batch_list=self._batch_list.quantity_of(self._product, self._batch),
            item_register=self._register.closing_balance(self._product),
        )

    def batch_quantity(self) -> Decimal:
        return self._batch_list.quantity_of(self._product, self._batch)

    def expect_moved_by(self, before: StockReading, change: Decimal) -> None:
        """Every view differs from the `before` reading by `change` (negative for a sale)."""
        expect_reading(self.read(), before.moved_by(change))


def expect_reading(found: StockReading, expected: StockReading) -> None:
    """Item List, Batch List and Item Register are each compared with their own expected figure."""
    pairs = (
        ("Item List", expected.item_list, found.item_list),
        ("Batch List", expected.batch_list, found.batch_list),
        ("Item Register", expected.item_register, found.item_register),
    )
    for view, wanted, shown in pairs:
        if wanted != shown:
            raise StockViewMismatchError(view, wanted, shown)


def views_of(page: Page, batch: str) -> StockViews:
    """The stock views of the stock test item (44646015) and one of its batches."""
    return StockViews(page, PRODUCT, batch)
