"""J16 multi-company: switching the active company, and data of one company staying out of another.

Plan: specs/multi-tenant.md (MT-01 to MT-04). Company A is the garments company the suite works in;
company B is a second organisation of the same login. Switching changes the login's selected company,
so every test switches back in teardown and the module runs on the tenant worker.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company.item_search import ItemSearch
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("multi-tenant"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ACCOUNT: Account = "garments"
# A second organisation of the same login, seen in the Organisation List on 2026-10-08.
OTHER_COMPANY = "General Billing 13_10"  # "NEW COMPANY 01-09" no longer exists on the tenant (2026-10-15)


@pytest.fixture
def companies(page_as: Callable[[Account], Page]) -> Iterator[CompanySwitchPage]:
    """The organisation switcher, starting in company A; the login's company is restored afterwards."""
    page = page_as(ACCOUNT)
    DashboardPage(page).open()
    DashboardPage(page).expect_menu_items(("Master",))
    switcher = CompanySwitchPage(page)
    original_company = switcher.stored_company_name().strip()
    switcher.ensure_company(GARMENTS_COMPANY)
    yield switcher
    switcher.ensure_company(original_company)


@pytest.fixture
def items(companies: CompanySwitchPage) -> ItemSearch:
    return ItemSearch(companies.page)


@pytest.fixture
def item_in_company_a(
    data: DataFactory, companies: CompanySwitchPage, items: ItemSearch
) -> Iterator[ItemMasterSpec]:
    """An item saved in company A by this test; deleted from company A afterwards."""
    item = data.item_master()
    _save_item(CreateItemPage(companies.page), item)
    yield item
    companies.ensure_company(GARMENTS_COMPANY)
    _delete_if_listed(items, item.product)


def test_switch_shows_the_chosen_company_in_the_header(companies: CompanySwitchPage) -> None:
    companies.switch_company(OTHER_COMPANY)

    companies.expect_header_company(OTHER_COMPANY)


def test_switch_stores_the_chosen_company_in_the_session(companies: CompanySwitchPage) -> None:
    companies.switch_company(OTHER_COMPANY)

    assert companies.stored_company_name().strip() == OTHER_COMPANY


def test_item_is_found_by_search_in_its_own_company(
    item_in_company_a: ItemMasterSpec, items: ItemSearch
) -> None:
    items.search(item_in_company_a.product)

    items.expect_found(item_in_company_a.product)


def test_item_of_one_company_is_not_found_in_another(
    item_in_company_a: ItemMasterSpec, companies: CompanySwitchPage, items: ItemSearch
) -> None:
    companies.switch_company(OTHER_COMPANY)

    items.search(item_in_company_a.product)

    items.expect_not_found(item_in_company_a.product)


def test_item_is_found_again_after_switching_back(
    item_in_company_a: ItemMasterSpec, companies: CompanySwitchPage, items: ItemSearch
) -> None:
    companies.switch_company(OTHER_COMPANY)
    companies.switch_company(GARMENTS_COMPANY)

    items.search(item_in_company_a.product)

    items.expect_found(item_in_company_a.product)


def _save_item(create_item: CreateItemPage, item: ItemMasterSpec) -> None:
    create_item.open()
    create_item.fill(item)
    create_item.save()
    create_item.expect_saved()
    create_item.decline_opening_stock()


def _delete_if_listed(items: ItemSearch, product: str) -> None:
    items.search(product)
    items.delete_if_found(product)
