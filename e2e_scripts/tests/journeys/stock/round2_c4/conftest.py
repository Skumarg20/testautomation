"""Fixtures for the stock rows of round 2 (part C4): the pharma company, a `Shop` that buys its own
batches and
cleans up, and a sale bill with held settings.

Teardown order, last set up first: held settings are put back (that needs a bill screen), the bill is left,
then the shop deletes the sale documents and the purchases that made the batches.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.sale.documents.flows import open_sales_page
from pages.sale.manual.option_settings import HeldOptions, SaleBillSettings
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.round2_c3.owned_stock import OwnedStock, StockFactory
from pages.stock.sale_impact.cleanup import Cleanup
from pages.stock.sale_impact.shop import Shop


@pytest.fixture
def sales_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.fixture
def cleanup() -> Iterator[Cleanup]:
    """The undo steps of the test's shop; a test that undoes something itself discards its step."""
    steps = Cleanup()
    yield steps
    steps.run_all()


@pytest.fixture
def shop(sales_page: Page, cleanup: Cleanup) -> Shop:
    return Shop(sales_page, cleanup)


@pytest.fixture
def batch(shop: Shop) -> str:
    """A batch of its own, bought for the test: 100 + 50 free of item 44646015."""
    return shop.buy_batch()


@pytest.fixture
def bill(sales_page: Page) -> Iterator[PharmaBill]:
    new_bill = PharmaBill(sales_page)
    yield new_bill
    if new_bill.is_open():
        new_bill.leave_without_saving()


@pytest.fixture
def options(sales_page: Page, bill: PharmaBill) -> Iterator[HeldOptions]:
    """Hold sale bill settings for this test; the tenant's originals are put back before the bill is left."""
    held = HeldOptions(SaleBillSettings(sales_page), bill.document.open_new, bill.leave_without_saving)
    yield held
    held.close()


@pytest.fixture
def stock_factory(sales_page: Page, run_id: str, cleanup: Cleanup) -> StockFactory:
    """Makes items of the test's own with batches (part C3's `OwnedStock`). Its removal is the first step
    registered, so it runs last: the sale documents and purchases of the test are deleted before the item."""
    stock = OwnedStock(sales_page, run_id)
    cleanup.add("owned stock", stock.dispose)
    return stock.create
