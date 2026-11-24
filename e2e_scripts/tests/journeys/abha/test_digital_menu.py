"""J39 the Digital > ABHA menu (AB-03, AB-04, AB-39): shown only for a chemist company with ABHA set up.

Menu entries are matched by the app's fixed menu ids (see `pages/abha/digital_menu.py`); nothing is opened
past the menu. The absence checks pass trivially if the id locator is wrong, so the first test is their
present-state counterpart.
"""

import pytest
from playwright.sync_api import Page

from pages.abha.digital_menu import DigitalMenu

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]

# Digital > ABHA entries in the L&D decks (`5 Billing.pptx#slide35-36`, KB `#17339c14`).
UPLOAD_ABHA_BILLS = "Upload ABHA Bills"
INCENTIVE_CLAIM = "Incentive Claim"


def _shown_menu(page: Page) -> DigitalMenu:
    menu = DigitalMenu(page)
    menu.wait_until_shown()
    return menu


def test_digital_menu_offers_abha_for_the_abha_company(abha_page: Page) -> None:
    _shown_menu(abha_page).expect_abha_entry_present()


def test_digital_menu_has_no_abha_when_the_abha_id_is_blank(chemist_without_abha_page: Page) -> None:
    _shown_menu(chemist_without_abha_page).expect_abha_entry_absent()


def test_digital_menu_is_hidden_when_abha_was_its_only_child(digital_with_only_abha: DigitalMenu) -> None:
    digital_with_only_abha.expect_digital_hidden()


def test_another_trade_has_no_abha_menu(non_chemist_page: Page) -> None:
    _shown_menu(non_chemist_page).expect_abha_entry_absent()


def test_abha_menu_offers_upload_abha_bills(abha_page: Page) -> None:
    menu = _shown_menu(abha_page)

    menu.open_abha()

    menu.expect_abha_offers(UPLOAD_ABHA_BILLS)


def test_abha_menu_offers_incentive_claim(abha_page: Page) -> None:
    menu = _shown_menu(abha_page)

    menu.open_abha()

    menu.expect_abha_offers(INCENTIVE_CLAIM)
