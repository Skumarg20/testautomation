"""Fixtures for the CRM tests: a garments session, the CRM screens and a loyalty setup put back afterwards."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.crm.crm_menu import CrmMenu
from pages.crm.home_delivery import HomeDelivery
from pages.crm.loyalty_setup import LoyaltySetup
from pages.crm.pending_approvals import PendingApprovals
from pages.dashboard_page import DashboardPage
from test_data.loyalty import LoyaltyEarning

# Only the garments company shows Loyalty Management under CRM (spec, CRM-01).
CRM_ACCOUNT: Account = "garments"


@pytest.fixture
def crm_page(page_as: Callable[[Account], Page]) -> Page:
    page = page_as(CRM_ACCOUNT)
    DashboardPage(page).open()
    # The login's company is shared state that other suites switch; the CRM menu was observed on this one.
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    return page


@pytest.fixture
def crm_menu(crm_page: Page) -> CrmMenu:
    return CrmMenu(crm_page)


@pytest.fixture
def pending_approvals(crm_page: Page) -> PendingApprovals:
    return PendingApprovals(crm_page)


@pytest.fixture
def home_delivery(crm_page: Page) -> HomeDelivery:
    return HomeDelivery(crm_page)


@pytest.fixture
def loyalty_setup(crm_page: Page) -> Iterator[LoyaltySetup]:
    """The company's loyalty setup, opened; the earning rule found is saved back in teardown."""
    setup = LoyaltySetup(crm_page)
    setup.open_from_menu()
    found = setup.current_earning()
    yield setup
    _restore(setup, found)


def _restore(setup: LoyaltySetup, earning: LoyaltyEarning) -> None:
    setup.reopen()  # a fresh start: a failed test can leave a dialog open
    if setup.current_earning() == earning:
        return
    setup.enter_earning(earning)
    setup.update()
    setup.expect_updated()
