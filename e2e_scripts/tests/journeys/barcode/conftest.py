"""Fixtures for the J27 barcode tests: a garments session, a barcode and items of this test.

Items without stock are deleted afterwards. An item with opening stock cannot be deleted (the app refuses
with "Opening Available In Main Store", specs/inventory.md D4), so it is left behind under its run id,
as the stock suite does. Sale bills are closed without saving."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.barcode.barcode_sale_bill import BarcodeSaleBill
from pages.barcode.barcode_settings import BarcodeDuplicateSetting
from pages.barcode.barcoded_item import BarcodedItem
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.inventory.item_list_page import ItemListPage
from test_data.barcodes import OPENING_QUANTITY, barcode_item, item_barcode, twin_item
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

BARCODE_ACCOUNT: Account = "garments"


@pytest.fixture
def barcode_page(page_as: Callable[[Account], Page]) -> Page:
    page = page_as(BARCODE_ACCOUNT)
    DashboardPage(page).open()
    # The login's company is shared state that other suites switch; the plan was observed on this one.
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    return page


@pytest.fixture
def barcode(run_id: str) -> str:
    return item_barcode(run_id)


@pytest.fixture
def barcoded_item(barcode_page: Page) -> BarcodedItem:
    return BarcodedItem(barcode_page)


@pytest.fixture
def item_spec(data: DataFactory, run_id: str) -> ItemMasterSpec:
    return barcode_item(data, run_id)


@pytest.fixture
def item_without_stock(barcode_page: Page, item_spec: ItemMasterSpec) -> Iterator[ItemMasterSpec]:
    """The item spec of this test; whatever the test saved under its name is deleted afterwards."""
    yield item_spec
    _delete_if_listed(barcode_page, item_spec)


@pytest.fixture
def saved_item(
    barcoded_item: BarcodedItem, item_without_stock: ItemMasterSpec, barcode: str
) -> ItemMasterSpec:
    barcoded_item.create(item_without_stock, barcode)
    return item_without_stock


@pytest.fixture
def twin(barcode_page: Page, data: DataFactory, run_id: str) -> Iterator[ItemMasterSpec]:
    item = twin_item(data, run_id)
    yield item
    _delete_if_listed(barcode_page, item)


@pytest.fixture
def stocked_item(barcoded_item: BarcodedItem, item_spec: ItemMasterSpec, barcode: str) -> ItemMasterSpec:
    """Saved with OPENING_QUANTITY in the main store; left on the tenant (see the module docstring)."""
    barcoded_item.create_with_opening(item_spec, barcode, OPENING_QUANTITY)
    return item_spec


@pytest.fixture
def sale_bill(barcode_page: Page) -> Iterator[BarcodeSaleBill]:
    """A new garments sale bill; request it after the item fixtures, as opening it leaves the item screens."""
    dashboard = DashboardPage(barcode_page)
    dashboard.open()
    dashboard.expect_menu_items(("Sale",))
    bill = BarcodeSaleBill(barcode_page)
    bill.open_new_bill()
    yield bill
    bill.leave_without_saving()


@pytest.fixture
def duplicates_forbidden(barcode_page: Page) -> Iterator[None]:
    """Sets "Barcode Duplicate allowed?" to No; the tenant's original choice is restored afterwards."""
    setting = BarcodeDuplicateSetting(barcode_page)
    original = setting.current()
    DashboardPage(barcode_page).open()
    setting.change_to("No")
    DashboardPage(barcode_page).open()  # a full reload, so the screens read the new setting
    yield
    DashboardPage(barcode_page).open()
    setting.change_to(original)


def _delete_if_listed(page: Page, item: ItemMasterSpec) -> None:
    DashboardPage(page).open()  # a fresh start: a failed test can leave a dialog open over the menu
    item_list = ItemListPage(page)
    item_list.open()
    if item_list.has_item(item.product):
        item_list.delete(item.product)
