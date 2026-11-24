"""Fixtures for the dashboard journey (J22): a chemist session on the garments company's dashboard.

The figures belong to the company, and the company and the chosen period belong to the login, which
other suites share; so the company is pinned and the period is chosen again after each test.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard.dashboard_links import DashboardLinks
from pages.dashboard.figures import DashboardFigures
from pages.dashboard.period_filter import PeriodFilter
from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

DASHBOARD_ACCOUNT: Account = "chemist"


@pytest.fixture
def dashboard_page(page_as: Callable[[Account], Page]) -> Page:
    page = page_as(DASHBOARD_ACCOUNT)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    DashboardFigures(page).open()
    return page


@pytest.fixture
def figures(dashboard_page: Page) -> DashboardFigures:
    return DashboardFigures(dashboard_page)


@pytest.fixture
def links(dashboard_page: Page) -> DashboardLinks:
    return DashboardLinks(dashboard_page)


@pytest.fixture
def period_filter(dashboard_page: Page) -> Iterator[PeriodFilter]:
    """The period picker; the period it showed at the start is chosen again afterwards."""
    picker = PeriodFilter(dashboard_page)
    period_at_start = picker.current_period()
    yield picker
    DashboardFigures(dashboard_page).open()
    if picker.label() != period_at_start.value:
        picker.choose(period_at_start)


@pytest.fixture
def add_own_item(data: DataFactory, dashboard_page: Page) -> Iterator[Callable[[], ItemMasterSpec]]:
    """Creates this test's item when called (Master > Item, no opening stock); deleted afterwards."""
    item = data.item_master()

    def add() -> ItemMasterSpec:
        screen = CreateItemPage(dashboard_page)
        screen.open()
        screen.fill(item)
        screen.save()
        screen.expect_saved()
        screen.decline_opening_stock()
        return item

    yield add
    DashboardPage(dashboard_page).open()
    item_list = ItemListPage(dashboard_page)
    item_list.open()
    if item_list.has_item(item.product):
        item_list.delete(item.product)
