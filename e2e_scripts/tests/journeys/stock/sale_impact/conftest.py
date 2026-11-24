"""Fixtures for the sale stock-impact tests: the pharma company and a `Shop` that cleans up after the test.

A batch of its own is bought for every test (purchase bill, 100 + 50 free), so a test sells from a batch it
made and never depends on what the shared QA stock holds.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.sale.documents.flows import open_sales_page
from pages.stock.sale_impact.cleanup import Cleanup
from pages.stock.sale_impact.shop import Shop


@pytest.fixture
def sales_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.fixture
def shop(sales_page: Page) -> Iterator[Shop]:
    cleanup = Cleanup()
    yield Shop(sales_page, cleanup)
    cleanup.run_all()


@pytest.fixture
def batch(shop: Shop) -> str:
    return shop.buy_batch()
