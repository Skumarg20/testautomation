"""J35 data-sync-offline: a request lost to the network sends the web app to "Website Under
Maintenance" and, once it can reach the server again, to the login screen, which logs the session out
(DS-05..DS-07, DS-24).

The expected values are the source's (`MrgHttpService.service.ts:467-479`, `errorpage.component.ts:53-65`,
`login.component.ts:336-343`). The pack flags the "maintenance" wording and the logout as a possible defect
(KB vs live 4, ticket MB-7335): the tests keep the source's behaviour; see D1 in the spec.
Every test runs in its own form login (`own_login_page`), because the logout ends that session on the server.
DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

import pytest
from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.data_sync.connection import Connectivity
from pages.data_sync.maintenance_page import MaintenancePage
from pages.data_sync.offline_bill import OfflineBill
from pages.data_sync.request_log import RequestLog
from pages.login_page import LoginPage

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]


@pytest.fixture
def maintenance_after_offline_save(own_login_page: Page, filled_offline_bill: OfflineBill) -> MaintenancePage:
    """The bill's keyboard save failed offline and the app showed the maintenance page; still offline."""
    Connectivity(own_login_page).go_offline()
    filled_offline_bill.save_with_keyboard()
    maintenance = MaintenancePage(own_login_page)
    maintenance.expect_shown()
    return maintenance


def test_offline_keyboard_save_shows_the_maintenance_page(
    own_login_page: Page, filled_offline_bill: OfflineBill
) -> None:
    Connectivity(own_login_page).go_offline()

    filled_offline_bill.save_with_keyboard()

    MaintenancePage(own_login_page).expect_shown()


def test_reconnecting_on_the_maintenance_page_logs_the_user_out(
    own_login_page: Page, maintenance_after_offline_save: MaintenancePage
) -> None:
    Connectivity(own_login_page).go_online()

    maintenance_after_offline_save.reload()

    maintenance_after_offline_save.expect_sent_to_login()
    _expect_session_ended(own_login_page)


def test_lost_bill_save_is_not_retried_after_reconnecting(
    own_login_page: Page, maintenance_after_offline_save: MaintenancePage, save_requests: RequestLog
) -> None:
    save_requests.forget_earlier()
    Connectivity(own_login_page).go_online()

    maintenance_after_offline_save.reload()

    maintenance_after_offline_save.expect_sent_to_login()
    assert save_requests.urls == (), f"DS-07: the lost save was sent again: {save_requests.urls}"


def test_opening_the_error_route_while_signed_in_logs_the_user_out(own_login_page: Page) -> None:
    maintenance = MaintenancePage(own_login_page)

    maintenance.open()

    maintenance.expect_shown()
    maintenance.expect_sent_to_login()
    _expect_session_ended(own_login_page)


def _expect_session_ended(page: Page) -> None:
    DashboardPage(page).open()
    LoginPage(page).expect_on_login_host()
