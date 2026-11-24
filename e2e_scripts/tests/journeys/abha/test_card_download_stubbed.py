"""J39 Download ABHA Card past the captcha (AB-26, AB-27), class b: each OTP call is answered by a stub.

The screen fixture has proven the session-token stub was hit. Each test installs the stub for the one OTP
call it triggers before typing the shown captcha, and proves it was served before checking the screen. The
verify and card calls that would follow are never stubbed, so the guard fails the test if one is tried.
"""

from re import Pattern

import pytest
from playwright.sync_api import Page

from pages.abha.abdm_endpoints import ADDRESS_NOT_REGISTERED_REPLY, OTP_SENT_REPLY, UNKNOWN_LOGIN_REPLY
from pages.abha.card_download_page import AbhaCardDownloadPage, DownloadMode
from pages.abha.messages import AADHAAR_NOT_REGISTERED, ABHA_ADDRESS_NOT_REGISTERED, OTP_REQUIRED
from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.masters.master_toasts import MasterToasts
from test_data.abha import FAKE_AADHAAR_PARTS, FAKE_ABHA_ADDRESS, FAKE_MOBILE

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]


def test_submit_otp_without_the_otp_is_refused(
    card_download: AbhaCardDownloadPage, login_otp: StubbedEndpoint, abha_page: Page
) -> None:
    login_otp.answer_with(OTP_SENT_REPLY)
    card_download.enter_mobile(FAKE_MOBILE)
    _send_with_shown_captcha(card_download, login_otp)
    card_download.expect_otp_box_shown()

    card_download.submit_otp()

    MasterToasts(abha_page).expect_warning_saying(OTP_REQUIRED)


def test_unregistered_abha_address_is_reported(
    card_download: AbhaCardDownloadPage, address_login_otp: StubbedEndpoint, abha_page: Page
) -> None:
    address_login_otp.answer_with(ADDRESS_NOT_REGISTERED_REPLY)
    card_download.choose(DownloadMode.ABHA_ADDRESS)
    card_download.enter_abha_address(FAKE_ABHA_ADDRESS)
    card_download.captcha.enter_shown_code()

    address_login_otp.capture_one(card_download.send_otp_to_abha_linked_mobile)

    _expect_warning(abha_page, ABHA_ADDRESS_NOT_REGISTERED)


def test_unregistered_aadhaar_is_reported(
    card_download: AbhaCardDownloadPage, login_otp: StubbedEndpoint, abha_page: Page
) -> None:
    login_otp.answer_with(UNKNOWN_LOGIN_REPLY)
    card_download.choose(DownloadMode.AADHAAR)
    card_download.enter_aadhaar(FAKE_AADHAAR_PARTS)

    _send_with_shown_captcha(card_download, login_otp)

    _expect_warning(abha_page, AADHAAR_NOT_REGISTERED)


def _send_with_shown_captcha(screen: AbhaCardDownloadPage, otp: StubbedEndpoint) -> None:
    screen.captcha.enter_shown_code()
    otp.capture_one(screen.send_otp)


def _expect_warning(page: Page, message: Pattern[str]) -> None:
    MasterToasts(page).expect_warning_saying(message)
