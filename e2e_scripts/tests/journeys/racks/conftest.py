"""Fixtures for the rack / warehouse tests: a chemist session on the garments company and own records."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.racks.item_rack import ItemRackField
from pages.racks.rack_master import RackForm, RackList
from pages.racks.rack_records import RackRecords
from pages.racks.rack_setting import RackMasterSetting
from pages.racks.store_master import StoreForm, StoreList
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec
from test_data.racks import RackDataFactory, RackSpec

RACKS_ACCOUNT: Account = "chemist"


@pytest.fixture
def racks_page(company_page: Callable[[Account, str], Page]) -> Page:
    return company_page(RACKS_ACCOUNT, GARMENTS_COMPANY)


@pytest.fixture
def records(racks_page: Page, run_id: str) -> Iterator[RackRecords]:
    """Stores and racks owned by this test; whatever is still listed afterwards is deleted."""
    owned = RackRecords(racks_page, RackDataFactory(run_id))
    yield owned
    DashboardPage(racks_page).open()  # a fresh start: a failed test can leave a form or dialog open
    owned.delete_all()


@pytest.fixture
def store_list(racks_page: Page) -> StoreList:
    return StoreList(racks_page)


@pytest.fixture
def store_form(racks_page: Page) -> StoreForm:
    return StoreForm(racks_page)


@pytest.fixture
def rack_list(racks_page: Page) -> RackList:
    return RackList(racks_page)


@pytest.fixture
def rack_form(racks_page: Page) -> RackForm:
    return RackForm(racks_page)


@pytest.fixture
def rack_field_page(racks_page: Page) -> Iterator[Page]:
    """The session with Control Room "Rack Master" = Yes for the test, then back to what it was.

    The setting is tenant-wide; it shows the Rack field on the item form."""
    setting = RackMasterSetting(racks_page)
    original = setting.current()
    if original != "Yes":
        setting.change_to("Yes")
    yield racks_page
    if original != "Yes":
        DashboardPage(racks_page).open()
        setting.change_to(original)


@pytest.fixture
def item_on_rack(
    rack_field_page: Page, records: RackRecords, data: DataFactory
) -> Iterator[tuple[ItemMasterSpec, RackSpec]]:
    """An item saved with a rack of this test; the item is deleted before the records (its rack) are."""
    rack = records.saved_rack(records.saved_store().name)
    item = data.item_master()
    form = CreateItemPage(rack_field_page)
    DashboardPage(rack_field_page).open()
    form.open()
    form.fill(item)
    ItemRackField(rack_field_page).choose(rack.name)
    form.save()
    form.expect_saved()
    form.decline_opening_stock()
    yield item, rack
    _delete_item(rack_field_page, item.product)


def _delete_item(page: Page, product: str) -> None:
    DashboardPage(page).open()
    items = ItemListPage(page)
    items.open()
    if items.has_item(product):
        items.delete(product)
