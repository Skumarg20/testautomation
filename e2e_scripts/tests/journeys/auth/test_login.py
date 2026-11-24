"""J01 login: trade-account sessions, the login form, logout and the not-authorized page."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

from config.settings import ACCOUNTS, Account, Credentials, settings
from pages.company_switch_page import CompanySwitchPage
from pages.components.not_authorized import NotAuthorizedPage
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage

GARMENTS: Account = "garments"
WRONG_PASSWORD = "Wrong#Pass123"
UNKNOWN_USER = "nosuchuser999@example.com"
STORED_USER_INFO_KEY = '{"key":"LoggedInUserInfo","session":"mb-session"}'
REMOVE_STORED_USER_INFO = f"() => localStorage.removeItem('{STORED_USER_INFO_KEY}')"
HAS_ACCESS_TOKEN = "() => Object.keys(localStorage).some(key => key.includes('access_token'))"
SESSION_STORAGE_KEYS = "() => Object.keys(sessionStorage)"
SESSION_KEY_NAMES = (
    "LoggedInUserInfo",
    "access_token",
    "RoleRight",
    "SortedFinYears",
    "checkedLinkId",
    "SessionId",
)
LOCAL_STORAGE_HOLDS = (
    "names => names.every(name => Object.keys(localStorage).some(key => key.includes(name)))"
)
SESSION_SAVED_TIMEOUT_MS = 60_000
USER_ID_MAX_LENGTH = "50"
PASSWORD_MAX_LENGTH = "16"

pytestmark = [pytest.mark.p0, pytest.mark.journey("auth")]


@pytest.mark.parametrize("account", ACCOUNTS)
def test_every_account_reaches_dashboard_with_stored_session(
    page_as: Callable[[Account], Page], account: Account
) -> None:
    dashboard = DashboardPage(page_as(account))

    dashboard.open()

    dashboard.expect_loaded()


def _real_user() -> str:
    credentials = settings.credentials(GARMENTS)
    if credentials is None:
        pytest.skip("No credentials for account garments (set QA_GARMENTS_USER/PASS)")
    return credentials.user


def _login_at_step_one(page: Page) -> LoginPage:
    login_page = LoginPage(page)
    login_page.open()
    return login_page


def test_wrong_password_stays_on_login(page: Page) -> None:
    login_page = _login_at_step_one(page)
    login_page.continue_with_user(_real_user())
    login_page.password.wait_for(state="visible")

    login_page.submit_password(WRONG_PASSWORD)

    login_page.expect_message("Please Enter The Valid Password !")
    login_page.expect_on_login_host()
    login_page.expect_password_step()
    assert not page.evaluate(HAS_ACCESS_TOKEN)


def test_empty_user_id_is_rejected(page: Page) -> None:
    login_page = _login_at_step_one(page)

    login_page.continue_with_user("")

    login_page.expect_message("Please Enter Mobile No. Or Email Id")
    expect(login_page.password).to_be_hidden()


def test_unknown_user_is_rejected(page: Page) -> None:
    login_page = _login_at_step_one(page)

    login_page.continue_with_user(UNKNOWN_USER)

    login_page.expect_message("Please Enter The Registered Mobile No. Or Email Id")
    expect(login_page.password).to_be_hidden()


def test_empty_password_is_rejected(page: Page) -> None:
    login_page = _login_at_step_one(page)
    login_page.continue_with_user(_real_user())
    login_page.password.wait_for(state="visible")

    login_page.submit_password("")

    login_page.expect_message("Please Enter Password")
    login_page.expect_password_step()
    expect(login_page.password_error_icon).to_be_attached()


@pytest.mark.parametrize("path", ["/dashboard", "/sale"])
def test_opening_a_page_without_a_session_redirects_to_login(page: Page, path: str) -> None:
    page.goto(f"{settings.margbooks_qa_url}{path}")

    LoginPage(page).expect_on_login_host()


def test_cleared_session_state_redirects_to_login(page_as: Callable[[Account], Page]) -> None:
    page = page_as(GARMENTS)
    DashboardPage(page).open()
    DashboardPage(page).expect_loaded()

    page.evaluate(REMOVE_STORED_USER_INFO)
    page.goto("/mstr/usermaster")

    LoginPage(page).expect_on_login_host()


def _sign_in_through_the_form(page: Page) -> DashboardPage:
    credentials = settings.credentials(GARMENTS)
    if credentials is None:
        pytest.skip("No credentials for account garments (set QA_GARMENTS_USER/PASS)")
    _login_at_step_one(page).sign_in(*credentials)
    dashboard = DashboardPage(page)
    dashboard.expect_loaded()
    return dashboard


def test_login_stores_the_session_in_local_storage_only(page: Page) -> None:
    _sign_in_through_the_form(page)

    page.wait_for_function(LOCAL_STORAGE_HOLDS, arg=list(SESSION_KEY_NAMES), timeout=SESSION_SAVED_TIMEOUT_MS)
    session_keys = " ".join(page.evaluate(SESSION_STORAGE_KEYS))

    assert "token" not in session_keys.lower(), session_keys


GARMENTS_IDENTIFIERS: dict[str, Callable[[], Credentials | None]] = {
    "primary": lambda: settings.credentials(GARMENTS),
    "alternate": settings.garments_alternate_credentials,
}


@pytest.mark.parametrize("identifier", GARMENTS_IDENTIFIERS)
def test_account_signs_in_with_each_of_its_identifiers(page: Page, identifier: str) -> None:
    credentials = GARMENTS_IDENTIFIERS[identifier]()
    if credentials is None:
        pytest.skip(
            f"AU-10: no {identifier} identifier for garments (QA_GARMENTS_USER / QA_GARMENTS_ALT_USER)"
        )

    _login_at_step_one(page).sign_in(*credentials)

    DashboardPage(page).expect_loaded()
    companies = CompanySwitchPage(page)
    companies.expect_header_company(companies.stored_company_name())


def test_login_fields_have_their_length_limits(page: Page) -> None:
    login_page = _login_at_step_one(page)

    expect(login_page.user_id).to_have_attribute("maxlength", USER_ID_MAX_LENGTH)
    expect(login_page.password).to_have_attribute("maxlength", PASSWORD_MAX_LENGTH)


def test_logout_lands_on_login_and_ends_the_session(page: Page) -> None:
    login_page = LoginPage(page)
    dashboard = _sign_in_through_the_form(page)

    dashboard.log_out()

    login_page.expect_on_login_host()
    assert not page.evaluate(HAS_ACCESS_TOKEN)
    page.goto(f"{settings.margbooks_qa_url}/dashboard")
    login_page.expect_on_login_host()


def test_unknown_route_shows_not_authorized_page(page_as: Callable[[Account], Page]) -> None:
    page = page_as(GARMENTS)
    DashboardPage(page).open()

    page.goto("/nosuchpage-xyz")

    NotAuthorizedPage(page).expect_shown()


def test_browser_back_after_logout_stays_on_login(page: Page) -> None:
    login_page = LoginPage(page)
    _sign_in_through_the_form(page).log_out()
    login_page.expect_on_login_host()

    page.go_back()

    login_page.expect_on_login_host()


@pytest.mark.skip(
    reason="AU-04: roles are tenant-defined by the supervisor (careportal:296923), so 'operator'/"
    "'accountant' are names, not fixed roles (Q5). Jira MBC-5372 says a user without View right must not "
    "open the list and must get an alert; careportal:308208 shows a 'Not Authorised' alert for a missing "
    "power. The route guard checks only the plan, not role rights (route-mapping.md 'Guards and rights'), "
    "so denial depends on each screen. Still needs a limited account (Q11: may tests create one?). "
    "Question (Q3): which alert text or redirect must a limited user get on a restricted URL?"
)
def test_limited_account_is_denied_restricted_pages() -> None: ...
