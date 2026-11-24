"""J39 AB-05: the ABHA screens opened by URL by a company that must not see ABHA.

Expected result from the pack: refused or redirected. The routes have only the login guard
(`app-routing.module.ts:52-56,163`, `Modules/abha.module.ts:24-26`), so these tests are expected to fail
today and report a defect; decision N2 in the spec confirms or withdraws that expectation. A screen that does
open asks for the ABDM session token, which the `session_token` stub answers.
"""

import pytest
from playwright.sync_api import Page

from pages.abha.card_download_page import AbhaCardDownloadPage
from pages.abha.registration_page import AbhaRegistrationPage

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("abha-health-flows"),
    pytest.mark.usefixtures("session_token"),
]


def test_registration_url_is_refused_for_another_trade(non_chemist_page: Page) -> None:
    AbhaRegistrationPage(non_chemist_page).open_expecting_refusal()


def test_card_download_url_is_refused_for_another_trade(non_chemist_page: Page) -> None:
    AbhaCardDownloadPage(non_chemist_page).open_expecting_refusal()


def test_registration_url_is_refused_when_the_abha_id_is_blank(chemist_without_abha_page: Page) -> None:
    AbhaRegistrationPage(chemist_without_abha_page).open_expecting_refusal()


def test_card_download_url_is_refused_when_the_abha_id_is_blank(chemist_without_abha_page: Page) -> None:
    AbhaCardDownloadPage(chemist_without_abha_page).open_expecting_refusal()
