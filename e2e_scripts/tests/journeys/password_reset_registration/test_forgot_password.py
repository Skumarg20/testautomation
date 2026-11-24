"""Forgot password up to, never past, the point where a reset mail or OTP would be sent (FP-01..FP-08).

Every test runs logged out with the OTP/mail endpoints blocked (`guarded_page`). Only fake identifiers are
submitted; the shared account is used once, to open the screen from the password step, and never submitted.
"""

import re

import pytest
from playwright.sync_api import Page, Request, expect

from config.settings import Account, settings
from pages.accounting.toasts import Toasts
from pages.auth.forgot_password_page import CAPTCHA_FORMAT, ForgotPasswordPage
from pages.login_page import LoginPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("password-reset-registration")]

GARMENTS: Account = "garments"
UNREGISTERED_ID = "nosuchuser999@example.com"
WRONG_CAPTCHA = "zzzz"
ACCOUNT_LOOKUP = "Loginuser/ValidLoginNew"
WRONG_CAPTCHA_MESSAGE = re.compile("Wrong captcha number", re.IGNORECASE)
UNREGISTERED_MESSAGE = re.compile("Please Enter The Registered Mobile No. Or Email Id", re.IGNORECASE)
RAW_SERVER_ERROR = re.compile("cannot be cast from DBNull", re.IGNORECASE)
RESPONSE_TIMEOUT_MS = 60_000


@pytest.fixture
def recovery(guarded_page: Page) -> ForgotPasswordPage:
    recovery_page = ForgotPasswordPage(guarded_page)
    recovery_page.open()
    return recovery_page


def test_forgot_password_link_opens_recovery_with_the_user_id_filled_in(guarded_page: Page) -> None:
    credentials = settings.credentials(GARMENTS)
    if credentials is None:
        pytest.skip("No credentials for account garments (set QA_GARMENTS_USER/PASS)")
    login_page = LoginPage(guarded_page)
    login_page.open()
    login_page.continue_with_user(credentials.user)
    login_page.password.wait_for(state="visible")

    guarded_page.get_by_role("link", name="Forgot Password").click()

    recovery_page = ForgotPasswordPage(guarded_page)
    recovery_page.expect_opened_for_a_user()
    expect(recovery_page.user_id).to_have_value(credentials.user)


def test_recovery_page_asks_for_id_and_captcha(recovery: ForgotPasswordPage) -> None:
    expect(recovery.user_id).to_be_visible()
    expect(recovery.captcha).to_have_attribute("maxlength", "4")
    expect(recovery.go_back_link).to_be_visible()
    assert CAPTCHA_FORMAT.match(recovery.shown_captcha()), recovery.shown_captcha()


def test_wrong_captcha_is_refused_before_any_account_lookup(recovery: ForgotPasswordPage) -> None:
    lookups: list[str] = []
    recovery.page.on("request", lambda request: _record_lookup(request, lookups))

    recovery.submit(UNREGISTERED_ID, WRONG_CAPTCHA)

    Toasts(recovery.page).expect_any_saying(WRONG_CAPTCHA_MESSAGE)
    recovery.expect_still_on_recovery()
    assert lookups == [], lookups


def test_empty_captcha_is_flagged_on_the_captcha_field(recovery: ForgotPasswordPage) -> None:
    recovery.submit(UNREGISTERED_ID, "")

    expect(recovery.captcha_error_icon).to_be_visible()
    recovery.expect_still_on_recovery()


def test_unregistered_id_is_refused(recovery: ForgotPasswordPage) -> None:
    recovery.submit_with_shown_captcha(UNREGISTERED_ID)

    Toasts(recovery.page).expect_any_saying(UNREGISTERED_MESSAGE, RESPONSE_TIMEOUT_MS)
    recovery.expect_still_on_recovery()


def test_empty_id_with_right_captcha_shows_no_raw_server_error(recovery: ForgotPasswordPage) -> None:
    with recovery.page.expect_response(re.compile(ACCOUNT_LOOKUP), timeout=RESPONSE_TIMEOUT_MS):
        recovery.submit_with_shown_captcha("")

    recovery.expect_still_on_recovery()
    # Why CSS: the notifier toast has no role; the app answers this lookup with a toast (seen live).
    answer = recovery.page.locator("notifier-notification").first
    expect(answer).to_be_visible()
    expect(answer).not_to_contain_text(RAW_SERVER_ERROR)


def test_captcha_refresh_draws_a_four_character_code(recovery: ForgotPasswordPage) -> None:
    recovery.captcha_refresh.click()

    assert CAPTCHA_FORMAT.match(recovery.shown_captcha()), recovery.shown_captcha()


def test_go_back_returns_to_login(recovery: ForgotPasswordPage) -> None:
    recovery.go_back_link.click()

    LoginPage(recovery.page).expect_on_login_host()
    expect(LoginPage(recovery.page).user_id).to_be_visible()


def _record_lookup(request: Request, lookups: list[str]) -> None:
    if ACCOUNT_LOOKUP in request.url:
        lookups.append(request.url)
