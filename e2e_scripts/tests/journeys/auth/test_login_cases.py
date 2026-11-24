"""Login cases. The case row names the scenario; credentials come from settings, never from Excel."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account, Credentials, settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.logout_page import LogoutPage
from test_data.document_cases import DocumentCase, case_id, cases_for

ACCOUNT: Account = "garments"
WRONG_PASSWORD = "Wrong#Pass123"
HAS_ACCESS_TOKEN = "() => Object.keys(localStorage).some(key => key.includes('access_token'))"
INVALID_PASSWORD_MESSAGE = "Please Enter The Valid Password !"

pytestmark = [pytest.mark.p1, pytest.mark.journey("auth")]


def _credentials() -> Credentials:
    credentials = settings.credentials(ACCOUNT)
    if credentials is None:
        pytest.skip(f"No credentials for account {ACCOUNT} (set QA_{ACCOUNT.upper()}_USER/PASS)")
    return credentials


def _open_login(page: Page) -> LoginPage:
    login_page = LoginPage(page)
    login_page.open()
    return login_page


def _valid_login_then_logout(page: Page) -> None:
    login_page = _open_login(page)
    login_page.sign_in(*_credentials())
    DashboardPage(page).expect_loaded()
    logout_page = LogoutPage(page)

    logout_page.log_out()

    login_page.expect_on_login_host()
    logout_page.expect_signed_out()


def _valid_user_wrong_password(page: Page) -> None:
    login_page = _open_login(page)
    login_page.continue_with_user(_credentials().user)
    login_page.password.wait_for(state="visible")

    login_page.submit_password(WRONG_PASSWORD)

    login_page.expect_message(INVALID_PASSWORD_MESSAGE)
    login_page.expect_password_step()
    assert not page.evaluate(HAS_ACCESS_TOKEN)


def _unregistered_user(page: Page) -> None:
    login_page = _open_login(page)

    login_page.continue_with_user("nosuchuser999@example.com")

    login_page.expect_message("Please Enter The Registered Mobile No. Or Email Id")
    assert not page.evaluate(HAS_ACCESS_TOKEN)


# Excel gives only the description ("valid data" / "invalid data"); TC_002 and TC_003 are identical there,
# so TC_002 is mapped to a wrong password and TC_003 to an unregistered user (unverified assumption).
_SCENARIOS: dict[str, Callable[[Page], None]] = {
    "TC_001": _valid_login_then_logout,
    "TC_002": _valid_user_wrong_password,
    "TC_003": _unregistered_user,
}


@pytest.mark.parametrize("case", cases_for("authentication", "login"), ids=case_id)
def test_login_case(page: Page, case: DocumentCase) -> None:
    _SCENARIOS[case.id](page)
