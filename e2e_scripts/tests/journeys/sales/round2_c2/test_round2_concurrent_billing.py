"""Ajay row 167: two logins billing at the same time keep bill numbers and data consistent.

Two sessions of the garments company: the worker's own and a second one signed in with the account's alternate
login (config.settings garments_alternate_credentials). Playwright's sync API is single-threaded, so "at
the same
time" is the harmful interleaving: both open a new bill (both see the same next number, OA-010), the first
saves, then the second saves. Expected: two different bill numbers, each in its own customer's list, and the
second save is not refused.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import BrowserContext, Page

from config.settings import settings
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.masters.round2_c2.owned_parties import OwnedParties
from pages.sale.round2_c2.party_and_type import OpenBillDesk

pytestmark = [pytest.mark.p2, pytest.mark.journey("sale-bill-creation")]

AMOUNT = Decimal(150)


@pytest.fixture
def second_page(context: BrowserContext) -> Page:
    credentials = settings.garments_alternate_credentials()
    if credentials is None:
        pytest.skip("row 167: no second garments login configured (QA_GARMENTS_ALT_USER)")
    page = context.new_page()
    login = LoginPage(page)
    login.open()
    login.sign_in(*credentials)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    return page


@pytest.fixture
def two_parties(guarded_page: Page, parties: OwnedParties) -> tuple[str, str]:
    first = parties.saved_with_email().name
    second = parties.saved_with_email().name
    PartyAvailability(guarded_page).wait_until_selectable(first)
    PartyAvailability(guarded_page).wait_until_selectable(second)
    return first, second


@pytest.fixture
def desks(
    guarded_page: Page, second_page: Page, zero_rated_item_name: str
) -> tuple[OpenBillDesk, OpenBillDesk]:
    return OpenBillDesk(guarded_page, zero_rated_item_name), OpenBillDesk(second_page, zero_rated_item_name)


def test_overlapping_saves_get_different_numbers(
    desks: tuple[OpenBillDesk, OpenBillDesk], two_parties: tuple[str, str]
) -> None:
    first, second = desks
    first.open_with_line(two_parties[0], AMOUNT)
    second.open_with_line(two_parties[1], AMOUNT)

    number_one = first.save_open_bill(two_parties[0])
    number_two = second.save_open_bill(two_parties[1])

    try:
        assert number_one != number_two
    finally:
        first.delete(number_one)
        second.delete(number_two)
