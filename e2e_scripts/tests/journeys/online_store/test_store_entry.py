"""J37 store entry: the Online Store router, the Sale > Online Order menu and the create-store form's prefill.

Scenario ids are those of scenarios/online-store.md; the plan is specs/online-store.md (DRAFT, not seen live).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.company_switch_page import CompanySwitchPage
from pages.online_store.create_store import CreateStorePage, StoreField
from pages.online_store.entry import ORDER_DASHBOARD_PATH, OnlineStoreMenu
from test_data.online_store import CLOSED_DAYS, OPEN_DAYS, WHOLE_DAY_END, WHOLE_DAY_START

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

STORE_TABS = ("Marg Mart", "Online Store")
DASHBOARD_TIMEOUT_MS = 60_000


def test_store_menu_without_a_store_offers_to_create_one(create_store_page: CreateStorePage) -> None:
    """OS-01: /other/onlinestore sends a company without a store to /other/createStore."""
    create_store_page.expect_banner()


@pytest.mark.parametrize("tab", STORE_TABS)
def test_create_store_offers_both_store_kinds(create_store_page: CreateStorePage, tab: str) -> None:
    """OS-01: the form has the tabs "Marg Mart" and "Online Store"."""
    create_store_page.start()
    create_store_page.expect_tab(tab)


def test_sale_online_order_opens_the_order_dashboard(store_page: Page) -> None:
    """OS-02: Sale > Online Order goes to /report/crm/E-Commerce/dashboard."""
    OnlineStoreMenu(store_page).open_online_order()
    expect(store_page).to_have_url(re.compile(re.escape(ORDER_DASHBOARD_PATH)), timeout=DASHBOARD_TIMEOUT_MS)


def test_store_name_is_prefilled_with_the_company_name(create_store_page: CreateStorePage) -> None:
    """OS-03: Store Name comes from the selected company (createForm, SelectedCompany.compname)."""
    company_name = CompanySwitchPage(create_store_page.page).stored_company_name()
    create_store_page.start()
    assert create_store_page.value_of(StoreField.STORE_NAME) == company_name


def test_working_hours_default_to_whole_day_nine_to_seven(create_store_page: CreateStorePage) -> None:
    """OS-03: Whole Day, 09:00 to 19:00."""
    create_store_page.start()
    assert create_store_page.whole_day_is_chosen()
    hours = (
        create_store_page.value_of(StoreField.WHOLE_DAY_START),
        create_store_page.value_of(StoreField.WHOLE_DAY_END),
    )
    assert hours == (WHOLE_DAY_START, WHOLE_DAY_END)


def test_working_days_default_to_monday_to_saturday(create_store_page: CreateStorePage) -> None:
    """OS-03: Monday to Saturday ticked, Sunday not."""
    create_store_page.start()
    ticked = tuple(day for day in OPEN_DAYS + CLOSED_DAYS if create_store_page.day_is_ticked(day))
    assert ticked == OPEN_DAYS
