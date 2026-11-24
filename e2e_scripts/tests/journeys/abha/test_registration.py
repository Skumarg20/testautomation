"""J39 ABHA Registration screen, UI only (AB-06..AB-09, AB-28): nothing past the Aadhaar boxes is sent."""

import pytest
from playwright.sync_api import Page, expect

from pages.abha.messages import AADHAAR_REQUIRED
from pages.abha.registration_page import AbhaRegistrationPage
from pages.dashboard_page import DashboardPage

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]


def test_registration_screen_shows_its_headings(registration: AbhaRegistrationPage) -> None:
    registration.expect_headings()


def test_registration_asks_for_aadhaar_in_three_boxes(registration: AbhaRegistrationPage) -> None:
    registration.expect_three_aadhaar_boxes()


def test_registration_links_to_card_download(registration: AbhaRegistrationPage) -> None:
    registration.expect_download_link()


def test_submit_without_aadhaar_is_refused(registration: AbhaRegistrationPage) -> None:
    registration.submit()

    registration.expect_refused_with(AADHAAR_REQUIRED)


def test_aadhaar_box_refuses_letters(registration: AbhaRegistrationPage) -> None:
    registration.type_into_aadhaar_box(0, "ab")

    expect(registration.aadhaar_box(0)).to_have_value("")


def test_aadhaar_box_takes_at_most_four_digits(registration: AbhaRegistrationPage) -> None:
    # Typing a fifth digit cannot show the limit: the fourth already moves the focus to the next box.
    expect(registration.aadhaar_box(0)).to_have_attribute("maxlength", "4")


def test_fourth_digit_moves_to_the_next_aadhaar_box(registration: AbhaRegistrationPage) -> None:
    registration.type_into_aadhaar_box(0, "0000")

    expect(registration.aadhaar_box(1)).to_be_focused()


def test_aadhaar_is_masked_by_default(registration: AbhaRegistrationPage) -> None:
    expect(registration.aadhaar_box(0)).to_have_attribute("type", "password")


def test_eye_icon_shows_the_aadhaar(registration: AbhaRegistrationPage) -> None:
    registration.show_aadhaar()

    expect(registration.aadhaar_box(0)).to_have_attribute("type", "text")


def test_close_returns_to_the_dashboard(registration: AbhaRegistrationPage, abha_page: Page) -> None:
    registration.close()

    DashboardPage(abha_page).expect_loaded()
