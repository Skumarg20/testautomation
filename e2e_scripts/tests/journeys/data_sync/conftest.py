"""Fixtures for the data sync / offline journey (J35): the web app's connection-loss handling and the
Data Sync request screen. DRAFT: written from the Angular source, not run against the app yet.

Three kinds of page:
- `layout_page`: the worker's shared chemist session on Garments New 29-08 (pinned, as in J22). Going
  offline is local to this test's own browser context, so it does not touch other tests.
- `sale_bill_page`: the same shared session on the pharma company, where the sales stored bill case lives.
- `own_login_page`: a fresh browser context signed in through the login form. Tests that end on `/error`
  and then `/login` use it, because the login screen logs the session out on the server
  (`login.component.ts:336-343`, `Common.service.ts:1455-1479`); doing that with the shared session would sign
  out every later test of the worker. Only the form login made here is logged out.
"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from playwright.sync_api import Browser, Page

from config.settings import Account, Credentials, settings, worker_index
from fixtures.session import MissingCredentialsError, report_missing_credentials
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.dashboard_page import DashboardPage
from pages.data_sync.connection import Connectivity
from pages.data_sync.internet_speed import INTERNET_SPEED_SWITCH, ReportedDownlink
from pages.data_sync.offline_bill import SAVE_ENDPOINT, OfflineBill
from pages.data_sync.offline_guards import OUTSIDE_CALLS
from pages.data_sync.request_log import RequestLog
from pages.data_sync.throwaway_company import ThrowawayCompany
from pages.login_page import LoginPage
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held
from test_data.data_sync import THROWAWAY_COMPANY

DATA_SYNC_ACCOUNT: Account = "chemist"
LIMITED_ACCOUNT: Account = "operator"
SERVICE_WORKER_READY_SCRIPT = (
    "() => navigator.serviceWorker ? navigator.serviceWorker.ready.then(() => true) : false"
)
SPEED_ON = SwitchValue(INTERNET_SPEED_SWITCH, "Yes")
SPEED_OFF = SwitchValue(INTERNET_SPEED_SWITCH, "No")
SLOW_LINK_MBPS = 1.0
FAST_LINK_MBPS = 50.0


@pytest.fixture
def layout_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    page = page_as(DATA_SYNC_ACCOUNT)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    yield page
    Connectivity(page).go_online()


@pytest.fixture
def connectivity(layout_page: Page) -> Connectivity:
    return Connectivity(layout_page)


@pytest.fixture
def sale_bill_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    page = page_as(DATA_SYNC_ACCOUNT)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(PHARMA_COMPANY)
    yield page
    Connectivity(page).go_online()


@pytest.fixture
def pharma_layout_page(sale_bill_page: Page) -> Page:
    """The shared session on the pharma company (business type 5, where the Drug Helpline link is offered)."""
    return sale_bill_page


@pytest.fixture
def own_login_page(page: Page, worker_id: str) -> Page:
    """A session of its own, from the login form, for a test that ends in the app's forced logout."""
    sign_in_through_form(page, worker_id)
    return page


@pytest.fixture
def sign_in_again(own_login_page: Page, worker_id: str) -> Callable[[], None]:
    """Signs the own-login page in again after the app logged it out, back on the pharma company."""

    def sign_in() -> None:
        sign_in_through_form(own_login_page, worker_id)
        CompanySwitchPage(own_login_page).ensure_company(PHARMA_COMPANY)

    return sign_in


@pytest.fixture
def guard_outside_calls() -> Iterator[Callable[[Page], None]]:
    """Arms a guard on a page that aborts any send or third-party call; fails the test if one was tried."""
    guards: list[SendGuard] = []

    def arm(page: Page) -> None:
        guard = SendGuard(page, OUTSIDE_CALLS)
        guard.arm()
        guards.append(guard)

    yield arm
    for guard in guards:
        guard.expect_nothing_sent()


@pytest.fixture
def throwaway_page(page_as: Callable[[Account], Page]) -> Page:
    """The shared session on the company kept for irreversible data sync requests; skips if missing."""
    page = page_as(DATA_SYNC_ACCOUNT)
    DashboardPage(page).open()
    company = ThrowawayCompany(page)
    if not company.is_listed(THROWAWAY_COMPANY):
        pytest.skip(f"DS-18/DS-19: needs the throwaway company {THROWAWAY_COMPANY!r} on the chemist login")
    company.select(THROWAWAY_COMPANY)
    return page


@pytest.fixture
def limited_user_page(page_as: Callable[[Account], Page]) -> Page:
    """A user with limited rights (the operator role); skips when the role has no credentials."""
    page = page_as(LIMITED_ACCOUNT)
    DashboardPage(page).open()
    return page


@pytest.fixture
def service_worker_page(
    browser: Browser, browser_context_args: dict[str, Any], worker_id: str
) -> Iterator[Page]:
    """A form login in a context that, unlike all others, lets the app register its service worker."""
    context = browser.new_context(**{**browser_context_args, "service_workers": "allow"})
    page = context.new_page()
    sign_in_through_form(page, worker_id)
    if not page.evaluate(SERVICE_WORKER_READY_SCRIPT):
        context.close()
        pytest.skip("DS-25: the build registers no service worker in this browser")
    yield page
    context.close()


def sign_in_through_form(page: Page, worker_id: str) -> None:
    login = LoginPage(page)
    login.open()
    login.sign_in(*_credentials_or_skip(DATA_SYNC_ACCOUNT, worker_id))
    DashboardPage(page).expect_loaded()


@pytest.fixture
def filled_offline_bill(own_login_page: Page) -> OfflineBill:
    """A filled sale bill on the pharma company in the test's own session; not saved."""
    CompanySwitchPage(own_login_page).ensure_company(PHARMA_COMPANY)
    bill = OfflineBill(own_login_page)
    bill.fill()
    return bill


@pytest.fixture
def save_requests(own_login_page: Page) -> RequestLog:
    return RequestLog(own_login_page, SAVE_ENDPOINT)


@pytest.fixture
def speed_shown_page(layout_page: Page) -> Iterator[Page]:
    """Control Room "Show Internet Speed" held at Yes for this test; the tenant's value is put back after."""
    yield from _with_speed_switch(layout_page, SPEED_ON)


@pytest.fixture
def speed_hidden_page(layout_page: Page) -> Iterator[Page]:
    """Control Room "Show Internet Speed" held at No for this test; the tenant's value is put back after."""
    yield from _with_speed_switch(layout_page, SPEED_OFF)


@pytest.fixture
def slow_link_page(layout_page: Page) -> Iterator[Page]:
    """The browser reports a 1 Mb/s link, then "Show Internet Speed" is held at Yes."""
    ReportedDownlink(layout_page.context).report(SLOW_LINK_MBPS)
    yield from _with_speed_switch(layout_page, SPEED_ON)


@pytest.fixture
def fast_link_page(layout_page: Page) -> Iterator[Page]:
    """The browser reports a 50 Mb/s link, then "Show Internet Speed" is held at Yes."""
    ReportedDownlink(layout_page.context).report(FAST_LINK_MBPS)
    yield from _with_speed_switch(layout_page, SPEED_ON)


def _with_speed_switch(page: Page, switch: SwitchValue) -> Iterator[Page]:
    dashboard = DashboardPage(page)
    # The restore starts online from the dashboard: a test may leave the browser offline.
    with switch_held(ControlRoomState(page), switch, lambda: _back_online_on(dashboard)):
        dashboard.open()  # a fresh load, so the layout reads the saved setting
        yield page


def _back_online_on(dashboard: DashboardPage) -> None:
    Connectivity(dashboard.page).go_online()
    dashboard.open()


def _credentials_or_skip(account: Account, worker_id: str) -> Credentials:
    """The worker's own user for the account, as `page_as` uses it."""
    credentials = settings.credentials(account, worker_index(worker_id))
    if credentials is None:
        report_missing_credentials(MissingCredentialsError(account))
    return credentials
