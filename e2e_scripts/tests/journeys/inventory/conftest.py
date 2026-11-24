"""Fixtures for item master tests: a logged-in page, the item screens and a test-owned item deleted after."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

ITEM_ACCOUNT: Account = "chemist"
# The company the item screens were observed on (specs/item-master-crud.md, Q-IC1).
ITEM_COMPANY = GARMENTS_COMPANY


@pytest.fixture
def item_page(company_page: Callable[[Account, str], Page]) -> Page:
    return company_page(ITEM_ACCOUNT, ITEM_COMPANY)


@pytest.fixture
def create_item(item_page: Page) -> CreateItemPage:
    return CreateItemPage(item_page)


@pytest.fixture
def item_list(item_page: Page) -> ItemListPage:
    return ItemListPage(item_page)


@pytest.fixture
def new_item(data: DataFactory, item_page: Page, item_list: ItemListPage) -> Iterator[ItemMasterSpec]:
    """An item owned by this test; if the test leaves it behind it is deleted (it has no transactions)."""
    item = data.item_master()
    yield item
    DashboardPage(item_page).open()  # a fresh start: a failed test can leave a dialog open over the menu
    item_list.open()
    if item_list.has_item(item.product):
        item_list.delete(item.product)


@pytest.fixture
def saved_item(create_item: CreateItemPage, new_item: ItemMasterSpec) -> ItemMasterSpec:
    create_item.open()
    create_item.fill(new_item)
    create_item.save()
    create_item.expect_saved()
    create_item.decline_opening_stock()
    return new_item
