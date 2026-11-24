"""J39 ABHA Registration after the OTP request (AB-14..AB-17), class b: the OTP call is answered by a stub.

Order inside each test: the screen fixture has already proven the session-token stub answered; the OTP
stub is installed before the consent is confirmed and proven to answer it before anything else is checked.
The enrolment call a correct captcha would make is never stubbed, so the guard fails the test if tried.
"""

import pytest
from playwright.sync_api import expect

from pages.abha.abdm_endpoints import UNKNOWN_LOGIN_REPLY
from pages.abha.captcha import WRONG_CAPTCHA
from pages.abha.consent_dialog import GiveConsent
from pages.abha.messages import AADHAAR_UNKNOWN, CAPTCHA_WRONG, MOBILE_REQUIRED
from pages.abha.registration_page import AbhaRegistrationPage
from test_data.abha import FAKE_MOBILE, FAKE_OTP

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]

OTP_LIMIT_INPUT = "1234567"
OTP_LIMIT_VALUE = "123456"


def test_unknown_aadhaar_is_reported(registration: AbhaRegistrationPage, consent_given: GiveConsent) -> None:
    consent_given(UNKNOWN_LOGIN_REPLY)

    registration.expect_refused_with(AADHAAR_UNKNOWN)


def test_submit_after_the_otp_without_a_mobile_is_refused(otp_stage: AbhaRegistrationPage) -> None:
    otp_stage.submit()

    otp_stage.expect_refused_with(MOBILE_REQUIRED)


def test_wrong_captcha_is_refused(otp_stage: AbhaRegistrationPage) -> None:
    otp_stage.enter_correspondence_mobile(FAKE_MOBILE)
    otp_stage.type_otp(FAKE_OTP)
    otp_stage.captcha.enter(WRONG_CAPTCHA)

    otp_stage.submit()

    otp_stage.expect_refused_with(CAPTCHA_WRONG)


def test_otp_box_keeps_six_digits(otp_stage: AbhaRegistrationPage) -> None:
    otp_stage.type_otp(OTP_LIMIT_INPUT)

    expect(otp_stage.otp_box).to_have_value(OTP_LIMIT_VALUE)


def test_resend_is_offered_up_to_two_times(otp_stage: AbhaRegistrationPage) -> None:
    otp_stage.expect_resend_limit_shown()


def test_mobile_note_is_shown_with_the_otp(otp_stage: AbhaRegistrationPage) -> None:
    otp_stage.expect_mobile_note_shown()
