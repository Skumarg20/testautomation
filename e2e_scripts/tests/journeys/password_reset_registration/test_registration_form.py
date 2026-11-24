"""Sign-up form checks that stop before an OTP is sent (RG-01..RG-06).

Logged out, OTP endpoints blocked (`guarded_page`). The only full-length mobile used starts with 1, which no
Indian mobile number does, and it is only submitted together with a referral code the app refuses first.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.accounting.toasts import Toasts
from pages.auth.registration_page import RegistrationPage
from pages.login_page import LoginPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("password-reset-registration")]

FAKE_MOBILE = "1000000001"
SHORT_MOBILE = "90810910"
UNKNOWN_REFERRAL_CODE = "JFDSJFHS"
TOO_SHORT_REFERRAL_CODE = "AB"
THREE_CHARACTER_REFERRAL_CODE = "ABC"
REFERRAL_LENGTH_MESSAGE = re.compile("Kindly enter at least 3 characters", re.IGNORECASE)
UNKNOWN_REFERRAL_MESSAGE = re.compile("Invalid Referral Code", re.IGNORECASE)
REFERRAL_LOOKUP = "User/GetPartnerDetailsBss"
RESPONSE_TIMEOUT_MS = 90_000


@pytest.fixture
def registration(guarded_page: Page) -> RegistrationPage:
    registration_page = RegistrationPage(guarded_page)
    registration_page.open()
    return registration_page


def test_sign_up_link_on_login_opens_registration(guarded_page: Page) -> None:
    login_page = LoginPage(guarded_page)
    login_page.open()

    guarded_page.get_by_role("link", name="Sign Up").click()

    registration_page = RegistrationPage(guarded_page)
    registration_page.expect_loaded()
    expect(registration_page.mobile).to_have_attribute("maxlength", "10")


@pytest.mark.parametrize("mobile", ["", SHORT_MOBILE], ids=["empty", "eight-digits"])
def test_send_otp_without_a_full_mobile_asks_for_a_valid_one(
    registration: RegistrationPage, mobile: str
) -> None:
    registration.request_otp_for(mobile)

    expect(registration.mobile_error).to_be_visible()
    registration.expect_still_on_mobile_step()


def test_mobile_field_drops_letters(registration: RegistrationPage) -> None:
    registration.type_mobile("abc12")

    expect(registration.mobile).to_have_value("12")


def test_mobile_field_stops_at_ten_digits(registration: RegistrationPage) -> None:
    registration.type_mobile("123456789012")

    expect(registration.mobile).to_have_value("1234567890")


def test_too_short_referral_code_is_refused(registration: RegistrationPage) -> None:
    registration.request_otp_with_referral(FAKE_MOBILE, TOO_SHORT_REFERRAL_CODE)

    Toasts(registration.page).expect_any_saying(REFERRAL_LENGTH_MESSAGE)
    registration.expect_still_on_mobile_step()


def test_three_character_referral_code_passes_the_length_check(registration: RegistrationPage) -> None:
    """The app's own message says three characters are enough; the code is then looked up, not refused."""
    with registration.page.expect_request(re.compile(REFERRAL_LOOKUP), timeout=RESPONSE_TIMEOUT_MS):
        registration.request_otp_with_referral(FAKE_MOBILE, THREE_CHARACTER_REFERRAL_CODE)

    registration.expect_still_on_mobile_step()


def test_unknown_referral_code_is_refused_before_any_otp(registration: RegistrationPage) -> None:
    registration.request_otp_with_referral(FAKE_MOBILE, UNKNOWN_REFERRAL_CODE)

    Toasts(registration.page).expect_any_saying(UNKNOWN_REFERRAL_MESSAGE, RESPONSE_TIMEOUT_MS)
    registration.expect_still_on_mobile_step()


def test_sign_in_link_returns_to_login(registration: RegistrationPage) -> None:
    registration.sign_in_link.click()

    LoginPage(registration.page).expect_on_login_host()
