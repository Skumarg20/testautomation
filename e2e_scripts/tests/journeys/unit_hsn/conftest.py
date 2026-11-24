"""Fixtures for J26: a garments session on its company, the unit and HSN screens, test-owned records."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from pages.inventory.item_list_page import ItemListPage
from pages.unit_hsn.hsn_form import HsnForm
from pages.unit_hsn.master_lists import HsnList, UnitList
from pages.unit_hsn.unit_form import UnitForm
from pages.unit_hsn.unit_hsn_records import UnitHsnRecords

UNIT_HSN_ACCOUNT: Account = "garments"


@pytest.fixture
def masters_page(company_page: Callable[[Account, str], Page]) -> Page:
    return company_page(UNIT_HSN_ACCOUNT, GARMENTS_COMPANY)


@pytest.fixture
def records(masters_page: Page, run_id: str) -> Iterator[UnitHsnRecords]:
    """Units, HSN codes and items owned by this test; whatever is still listed afterwards is deleted."""
    owned = UnitHsnRecords(masters_page, run_id)
    yield owned
    DashboardPage(masters_page).open()  # a fresh start: a failed test can leave a dialog open
    owned.delete_all()


@pytest.fixture
def unit_list(masters_page: Page) -> UnitList:
    return UnitList(masters_page)


@pytest.fixture
def unit_form(masters_page: Page) -> UnitForm:
    return UnitForm(masters_page)


@pytest.fixture
def hsn_list(masters_page: Page) -> HsnList:
    return HsnList(masters_page)


@pytest.fixture
def hsn_form(masters_page: Page) -> HsnForm:
    return HsnForm(masters_page)


@pytest.fixture
def item_list(masters_page: Page) -> ItemListPage:
    return ItemListPage(masters_page)
