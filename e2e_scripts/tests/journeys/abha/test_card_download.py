"""J39 Download ABHA Card, UI only (AB-21..AB-25, AB-28): every send is refused by the screen's own checks.

No OTP stub is installed here, so an OTP request the checks let through would be aborted and reported by the
AbdmGuard when the test ends.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.abha.captcha import WRONG_CAPTCHA
from pages.abha.card_download_page import AbhaCardDownloadPage, DownloadMode
from pages.abha.messages import (
    ABHA_ADDRESS_REQUIRED,
    CAPTCHA_REQUIRED,
    CAPTCHA_WRONG,
    DOWNLOAD_AADHAAR_REQUIRED,
    DOWNLOAD_MOBILE_REQUIRED,
    FULL_ABHA_NUMBER_REQUIRED,
)
from pages.dashboard_page import DashboardPage
from pages.masters.master_toasts import MasterToasts
from test_data.abha import FAKE_MOBILE

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]

FIRST_ABHA_NUMBER_PART = "00"


def test_download_screen_shows_its_heading(card_download: AbhaCardDownloadPage) -> None:
    card_download.expect_heading()


def test_download_offers_mobile_aadhaar_abha_number_and_address(card_download: AbhaCardDownloadPage) -> None:
    card_download.expect_every_mode_offered()


def test_download_starts_with_mobile(card_download: AbhaCardDownloadPage) -> None:
    card_download.expect_mode_chosen(DownloadMode.MOBILE)


def test_send_otp_without_a_mobile_is_refused(card_download: AbhaCardDownloadPage, abha_page: Page) -> None:
    card_download.send_otp()

    MasterToasts(abha_page).expect_warning_saying(DOWNLOAD_MOBILE_REQUIRED)


def test_send_otp_with_part_of_the_abha_number_is_refused(
    card_download: AbhaCardDownloadPage, abha_page: Page
) -> None:
    card_download.choose(DownloadMode.ABHA_NUMBER)
    card_download.enter_abha_number_part(1, FIRST_ABHA_NUMBER_PART)

    card_download.send_otp_to_abha_linked_mobile()

    MasterToasts(abha_page).expect_warning_saying(FULL_ABHA_NUMBER_REQUIRED)


def test_incomplete_abha_number_puts_the_cursor_in_the_first_empty_part(
    card_download: AbhaCardDownloadPage,
) -> None:
    card_download.choose(DownloadMode.ABHA_NUMBER)
    card_download.enter_abha_number_part(1, FIRST_ABHA_NUMBER_PART)

    card_download.send_otp_to_abha_linked_mobile()

    expect(card_download.abha_number_box(2)).to_be_focused()


def test_send_otp_without_an_abha_address_is_refused(
    card_download: AbhaCardDownloadPage, abha_page: Page
) -> None:
    card_download.choose(DownloadMode.ABHA_ADDRESS)

    card_download.send_otp_to_abha_linked_mobile()

    MasterToasts(abha_page).expect_warning_saying(ABHA_ADDRESS_REQUIRED)
    expect(card_download.abha_address_box).to_be_focused()


def test_send_otp_without_an_aadhaar_is_refused(card_download: AbhaCardDownloadPage, abha_page: Page) -> None:
    card_download.choose(DownloadMode.AADHAAR)

    card_download.send_otp()

    MasterToasts(abha_page).expect_warning_saying(DOWNLOAD_AADHAAR_REQUIRED)
    expect(card_download.aadhaar_box(1)).to_be_focused()


def test_send_otp_without_the_captcha_is_refused(
    card_download: AbhaCardDownloadPage, abha_page: Page
) -> None:
    card_download.enter_mobile(FAKE_MOBILE)

    card_download.send_otp()

    MasterToasts(abha_page).expect_warning_saying(CAPTCHA_REQUIRED)
    card_download.captcha.expect_focused()


def test_send_otp_with_a_wrong_captcha_is_refused(
    card_download: AbhaCardDownloadPage, abha_page: Page
) -> None:
    card_download.enter_mobile(FAKE_MOBILE)
    card_download.captcha.enter(WRONG_CAPTCHA)

    card_download.send_otp()

    MasterToasts(abha_page).expect_warning_saying(CAPTCHA_WRONG)
    card_download.captcha.expect_focused()


def test_close_returns_to_the_dashboard(card_download: AbhaCardDownloadPage, abha_page: Page) -> None:
    card_download.close()

    DashboardPage(abha_page).expect_loaded()
