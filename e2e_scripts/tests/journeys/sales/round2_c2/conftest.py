"""Fixtures of the round-2 (part C2) sale cases: garments login, sends guarded, test-owned parties and
items."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.exempt_item import ExemptItem
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.dashboard_page import DashboardPage
from pages.masters.round2_c2.owned_items import OwnedItems
from pages.masters.round2_c2.owned_parties import OwnedParties
from pages.notifications_export.delivery_endpoints import WHATSAPP_SEND
from pages.sale.round2_c2.email_sms import SEND_GUARD
from test_data.factory import DataFactory

GARMENTS: Account = "garments"


@pytest.fixture
def guarded_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    """The garments dashboard with every mail, SMS and WhatsApp send aborted unless a test stubs it."""
    page = page_as(GARMENTS)
    guards = [SendGuard(page, SEND_GUARD), SendGuard(page, WHATSAPP_SEND)]
    for guard in guards:
        guard.arm()
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    yield page
    for guard in guards:
        guard.expect_nothing_sent()


@pytest.fixture
def parties(guarded_page: Page, run_id: str) -> Iterator[OwnedParties]:
    owned = OwnedParties(guarded_page, run_id)
    yield owned
    owned.delete_all()


@pytest.fixture
def items(guarded_page: Page, data: DataFactory) -> Iterator[OwnedItems]:
    owned = OwnedItems(guarded_page, data)
    yield owned
    owned.delete_unused()


@pytest.fixture
def zero_rated_item_name(guarded_page: Page) -> str:
    return ExemptItem(guarded_page).ensure_exists()


@pytest.fixture
def stock_page(company_page: Callable[[Account, str], Page]) -> Page:
    """The chemist login on the garments company, where the stock screens were observed."""
    return company_page("chemist", GARMENTS_COMPANY)
