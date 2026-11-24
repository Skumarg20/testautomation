"""Fixtures for the stock movement tests: a chemist session and an item of this test with opening stock.

The item cannot be deleted afterwards: the app refuses with "Opening Available In Main Store" once an item
has opening stock (specs/inventory.md, NEEDS DECISION D4), so it is left behind under its run id.
"""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY
from pages.stock.opening_stock import create_item_with_opening
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec
from test_data.stock_movement import OPENING_QUANTITY
from test_data.stock_movement import stock_item as journey_item

STOCK_ACCOUNT: Account = "chemist"


@pytest.fixture
def stock_page(company_page: Callable[[Account, str], Page]) -> Page:
    return company_page(STOCK_ACCOUNT, GARMENTS_COMPANY)


@pytest.fixture
def stock_item(data: DataFactory, run_id: str) -> ItemMasterSpec:
    return journey_item(data, run_id)


@pytest.fixture
def item_with_opening_stock(stock_page: Page, stock_item: ItemMasterSpec) -> ItemMasterSpec:
    """The item, saved with OPENING_QUANTITY in the main store through the "add item Opening?" window."""
    create_item_with_opening(stock_page, stock_item, OPENING_QUANTITY)
    return stock_item
