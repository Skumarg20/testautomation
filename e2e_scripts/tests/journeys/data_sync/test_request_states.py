"""J35 data-sync-offline: how the web app reacts to each data sync request state, with the state answered by a
stub (DS-19 confirmation, DS-20, DS-21) and the screen's access rule (DS-22).

The QA companies must never get a real request (DS-18/19 are irreversible), so `SyncStatusStub` answers the
status call in the browser for one company and "no request" for any other. Nothing is written on the server;
`SyncRequestsave` is aborted by a guard in the confirmation test and the answer is never "Yes".
DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Page

from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.components.confirm_dialog import ConfirmDialog
from pages.components.send_guard import SendGuard
from pages.dashboard_page import DashboardPage
from pages.data_sync.data_sync_screen import REQUEST_ENDPOINT, DataSyncScreen, SyncRequestState
from pages.data_sync.sync_status_stub import CompanyKeys, RequestStatus, SyncStatusStub
from pages.data_sync.transaction_lock import TransactionLock

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]

CANCEL_QUESTION = "You Won't be able to send request again. Are you sure want to cancel ?"


def _stub_and_reload(page: Page, status: RequestStatus) -> SyncStatusStub:
    """Answers the selected company's status with `status` and reloads, so the layout asks again."""
    stub = SyncStatusStub(page, CompanyKeys.of_selected_company(page), status)
    stub.install()
    DashboardPage(page).open()
    return stub


@pytest.fixture
def approved_pharma_page(pharma_layout_page: Page) -> Page:
    """The pharma company (whose sale bill screen the suite knows), seen as one with an approved request."""
    _stub_and_reload(pharma_layout_page, RequestStatus.APPROVED)
    return pharma_layout_page


@pytest.fixture
def approved_garments_page(layout_page: Page) -> Page:
    """The garments company seen as one with an approved request; any other company has none."""
    _stub_and_reload(layout_page, RequestStatus.APPROVED)
    return layout_page


@pytest.fixture
def pending_request_screen(layout_page: Page) -> Iterator[DataSyncScreen]:
    """The Data Sync screen showing a pending request (stubbed); any real request save is aborted."""
    guard = SendGuard(layout_page, REQUEST_ENDPOINT)
    guard.arm()
    _stub_and_reload(layout_page, RequestStatus.PENDING)
    screen = DataSyncScreen(layout_page)
    screen.open()
    yield screen
    guard.expect_nothing_sent()


def test_approved_request_locks_new_sale_bills(approved_pharma_page: Page) -> None:
    lock = TransactionLock(approved_pharma_page)

    lock.try_new_sale_bill()

    lock.expect_locked()


def test_cancel_asks_for_confirmation_before_sending(pending_request_screen: DataSyncScreen) -> None:
    pending_request_screen.press_cancel()

    dialog = ConfirmDialog(pending_request_screen.page)
    dialog.expect_asking(CANCEL_QUESTION)
    dialog.answer_no()
    pending_request_screen.expect_state(SyncRequestState.PENDING)


def test_other_company_shows_its_own_request_state(approved_pharma_page: Page) -> None:
    CompanySwitchPage(approved_pharma_page).ensure_company(GARMENTS_COMPANY)
    screen = DataSyncScreen(approved_pharma_page)

    screen.open()

    screen.expect_state(SyncRequestState.NO_REQUEST)


def test_lock_of_one_company_does_not_reach_another(approved_garments_page: Page) -> None:
    CompanySwitchPage(approved_garments_page).ensure_company(PHARMA_COMPANY)
    lock = TransactionLock(approved_garments_page)

    lock.try_new_sale_bill()

    lock.expect_bill_form_opened()


def test_limited_user_reaches_the_data_sync_screen_by_url(limited_user_page: Page) -> None:
    screen = DataSyncScreen(limited_user_page)

    screen.open()

    screen.expect_company_email()
