"""Fixtures for J21 notifications-export (specs/notifications-export.md).

Every page is armed with the send guard (`pages/components/send_guard.py`) before its first navigation:
it aborts any send, schedule save, notification insert or profile save.
A test fails in teardown if the screen tried one of them.

The chemist login's company is shared state, so it is pinned to the garments company; the few tests that need
the pharma (chemist trade) company switch to it and back, and run in the "chemist-tenant" xdist group.
Data a test makes (ledgers, customers, sale bills) is deleted in teardown.
"""

from collections.abc import Callable, Iterator
from dataclasses import replace
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.exempt_item import ExemptItem
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.banking.bank_book import BankBook
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.dashboard_page import DashboardPage
from pages.masters.master_records import MasterRecords
from pages.notifications_export.bill_preview import PreviewedSaleBillDesk
from pages.notifications_export.delivery_endpoints import DELIVERY_OR_GLOBAL_WRITE
from pages.notifications_export.notification_bell import NotificationBell
from pages.notifications_export.notification_feed import NOTIFICATION_LIST, FeedItem, NotificationFeed
from test_data.banking import BankLedgers, bank_ledgers
from test_data.factory import DataFactory
from test_data.masters import MasterDataFactory
from test_data.notifications_export import BILL_AMOUNT, HINDI_WORD, OwnedBill, PreviewedBill

JOURNEY_ACCOUNT: Account = "chemist"
LEDGER_ACCOUNT: Account = "garments"


@pytest.fixture
def guarded_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    """A chemist page, guarded, not yet navigated."""
    page = page_as(JOURNEY_ACCOUNT)
    guard = SendGuard(page, DELIVERY_OR_GLOBAL_WRITE)
    guard.arm()
    yield page
    guard.expect_nothing_sent()


@pytest.fixture
def guarded_page_as(page_as: Callable[[Account], Page]) -> Iterator[Callable[[Account], Page]]:
    """Like `page_as`, with every page armed with the send guard before its first navigation."""
    guards: list[SendGuard] = []

    def open_guarded(account: Account) -> Page:
        page = page_as(account)
        guard = SendGuard(page, DELIVERY_OR_GLOBAL_WRITE)
        guard.arm()
        guards.append(guard)
        return page

    yield open_guarded
    for guard in guards:
        guard.expect_nothing_sent()


@pytest.fixture
def journey_page(guarded_page: Page) -> Page:
    """The guarded chemist page on the dashboard of the garments company."""
    _open_dashboard_of_garments(guarded_page)
    return guarded_page


@pytest.fixture
def bell_showing(guarded_page: Page) -> Callable[[list[FeedItem]], NotificationBell]:
    """Opens the dashboard with the bell fed `items` instead of the global Marg feed."""

    def open_with(items: list[FeedItem]) -> NotificationBell:
        feed = NotificationFeed(guarded_page)
        feed.serve(items)
        feed.serve_link_target()
        _open_dashboard_of_garments(guarded_page)
        return NotificationBell(guarded_page)

    return open_with


@pytest.fixture
def notification_list_url(guarded_page: Page) -> str:
    """The URL the app itself calls for the bell's list (gateway host and API version included)."""
    with guarded_page.expect_request(NOTIFICATION_LIST) as request:
        _open_dashboard_of_garments(guarded_page)
    return request.value.url


@pytest.fixture
def pharma_page(guarded_page: Page) -> Iterator[Page]:
    """The guarded chemist page in the pharma (chemist trade) company; put back in garments afterwards."""
    DashboardPage(guarded_page).open()
    CompanySwitchPage(guarded_page).ensure_company(PHARMA_COMPANY)
    yield guarded_page
    _open_dashboard_of_garments(guarded_page)


@pytest.fixture
def ledger_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    """A garments-login page, guarded, not yet navigated."""
    page = page_as(LEDGER_ACCOUNT)
    guard = SendGuard(page, DELIVERY_OR_GLOBAL_WRITE)
    guard.arm()
    yield page
    guard.expect_nothing_sent()


@pytest.fixture
def garments_page(ledger_page: Page) -> Page:
    """The guarded garments-login page on the dashboard of the garments company."""
    _open_dashboard_of_garments(ledger_page)
    return ledger_page


@pytest.fixture
def ledger_book(ledger_page: Page, data: DataFactory) -> Iterator[BankBook]:
    """Like `bank_book` (fixtures/bank_book.py), but guarded before the first navigation."""
    yield from _book_of(ledger_page, bank_ledgers(data))


@pytest.fixture
def hindi_ledger_book(ledger_page: Page, data: DataFactory) -> Iterator[BankBook]:
    """`ledger_book` whose expense ledger's name ends in a Hindi word (NE-23)."""
    ledgers = bank_ledgers(data)
    expense = replace(ledgers.expense, name=f"{ledgers.expense.name} {HINDI_WORD}")
    yield from _book_of(ledger_page, replace(ledgers, expense=expense))


@pytest.fixture
def owned_customer(garments_page: Page, run_id: str) -> Iterator[str]:
    """A new customer ledger, deleted after the test (after its bills: fixtures tear down in reverse)."""
    records = MasterRecords(garments_page, MasterDataFactory(run_id))
    try:
        name = records.saved_customer().name
        PartyAvailability(garments_page).wait_until_selectable(name)
        yield name
    finally:
        records.delete_all()


@pytest.fixture
def exempt_item(garments_page: Page) -> str:
    """The outstanding journey's 0% GST item, so a bill's total is its line amount."""
    return ExemptItem(garments_page).ensure_exists()


@pytest.fixture
def customer_bill(garments_page: Page, owned_customer: str, exempt_item: str) -> Iterator[OwnedBill]:
    """One unpaid sale bill for the test's own customer; deleted after the test."""
    desk = SaleBillDesk(garments_page, exempt_item)
    number = desk.create(owned_customer, BILL_AMOUNT, Decimal(0))
    yield OwnedBill(owned_customer, number, BILL_AMOUNT)
    desk.delete(number)


@pytest.fixture
def previewed_bill(garments_page: Page, owned_customer: str, exempt_item: str) -> Iterator[PreviewedBill]:
    """An unpaid sale bill whose Print window was previewed, then closed; deleted after the test."""
    desk = PreviewedSaleBillDesk(garments_page, exempt_item)
    number = desk.create_unpaid(owned_customer, BILL_AMOUNT)
    yield PreviewedBill(number, BILL_AMOUNT, desk.preview)
    desk.delete(number)


def _book_of(page: Page, ledgers: BankLedgers) -> Iterator[BankBook]:
    book = BankBook(page, ledgers)
    try:
        book.open()
        yield book
    finally:
        book.close()


def _open_dashboard_of_garments(page: Page) -> None:
    dashboard = DashboardPage(page)
    dashboard.open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    dashboard.expect_loaded()
