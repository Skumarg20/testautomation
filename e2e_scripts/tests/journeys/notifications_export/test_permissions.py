"""J21 permission checks (specs/notifications-export.md, NE-38..NE-41). Read-only: nothing is typed into
the admin screen and no admin password is used.

NE-38/39 need a user whose role lacks the right. The suite's limited accounts ("operator", "accountant") are
tried in turn; a test skips when the account has no credentials or its role does have the right (read from
the role's menu the app keeps after login, `pages/notifications_export/menu_rights.py`)."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, Playwright

from config.settings import Account
from pages.components.access_denied import AccessDenied
from pages.dashboard_page import DashboardPage
from pages.notifications_export.anonymous_call import ApiAnswer, anonymous_get
from pages.notifications_export.menu_rights import MenuRights, menu_rights
from pages.notifications_export.prescription_reminder_page import PATH as PRESCRIPTION_REMINDER_PATH
from pages.notifications_export.report_share_export import ReportShareExport
from pages.reports.accounting_reports import TrialBalancePage

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

CREATE_NOTIFICATION_PATH = "/admin/support/create-notification"
NO_TENANT_ANSWER = ApiAnswer(status_code="417", error_message="Dbinfolinkid is zero", has_data=False)
LIMITED_ACCOUNTS: tuple[Account, ...] = ("operator", "accountant")
PRESCRIPTION_REMINDER_MENU = "Prescription Reminder"
TRIAL_BALANCE_MENU = "Trial Balance"


def _signed_in(
    guarded_page_as: Callable[[Account], Page], account: Account
) -> tuple[Page, Callable[[str], MenuRights]]:
    page = guarded_page_as(account)
    DashboardPage(page).open()
    return page, lambda menu: menu_rights(page, menu)


def test_notification_list_without_login_is_refused(
    playwright: Playwright, notification_list_url: str
) -> None:
    """NE-40: NotificationList is AllowAnonymous; without a tenant it answers 417 "Dbinfolinkid is zero"
    (in the body's status; the HTTP status is 200) and no data."""
    assert anonymous_get(playwright, notification_list_url) == NO_TENANT_ANSWER


def test_create_notification_screen_is_refused_to_a_tenant_user(journey_page: Page) -> None:
    """NE-41: like its sibling /admin/support/notification, the global Create Notification screen should
    not open for a tenant user. The route has no guard (K10), so this is expected to fail (D4)."""
    AccessDenied(journey_page).expect_denied(CREATE_NOTIFICATION_PATH)


@pytest.mark.parametrize("account", LIMITED_ACCOUNTS)
def test_prescription_reminder_is_refused_without_the_crm_right(
    guarded_page_as: Callable[[Account], Page], account: Account
) -> None:
    """NE-38: a role without CRM > Prescription Reminder cannot open the screen by its address."""
    page, rights = _signed_in(guarded_page_as, account)
    if rights(PRESCRIPTION_REMINDER_MENU).can_view:
        pytest.skip(f"NE-38: {account} has the Prescription Reminder right; needs a role without it (Q7)")

    AccessDenied(page).expect_denied(PRESCRIPTION_REMINDER_PATH)


@pytest.mark.parametrize("account", LIMITED_ACCOUNTS)
def test_report_offers_no_export_without_the_export_right(
    guarded_page_as: Callable[[Account], Page], account: Account
) -> None:
    """NE-39: a role whose Trial Balance right has Export off sees no Excel or PDF icon there.
    UNVERIFIED in the pack: the report toolbar (sharedexportimport.ts) checks no right; the import/export
    button does (importexport.component.ts:524-532)."""
    page, rights = _signed_in(guarded_page_as, account)
    trial_balance = rights(TRIAL_BALANCE_MENU)
    if not trial_balance.can_view or trial_balance.can_export:
        pytest.skip(f"NE-39: {account} needs Trial Balance with view but without export (Q7)")
    TrialBalancePage(page).open()

    ReportShareExport(page).expect_no_export_icons()
