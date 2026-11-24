from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import BOOKS_PERIOD, CompanySwitchPage
from pages.dashboard_page import DashboardPage

pytestmark = [pytest.mark.p0, pytest.mark.journey("company-financial-year")]

ACCOUNT: Account = "garments"
NO_SUCH_ORGANISATION = "zzz-no-such-organisation-999"


@pytest.fixture
def companies(page_as: Callable[[Account], Page]) -> CompanySwitchPage:
    page = page_as(ACCOUNT)
    DashboardPage(page).open()
    DashboardPage(page).expect_loaded()
    return CompanySwitchPage(page)


def test_header_shows_the_stored_active_company(companies: CompanySwitchPage) -> None:
    companies.expect_header_company(companies.stored_company_name())


def test_header_shows_a_books_year(companies: CompanySwitchPage) -> None:
    assert BOOKS_PERIOD.fullmatch(companies.current_year())


def test_profile_card_shows_the_header_company_and_books_year(companies: CompanySwitchPage) -> None:
    company, books_period = companies.stored_company_name(), companies.current_year()

    companies.open_profile_card()

    companies.expect_profile_card_shows(company, books_period)


def test_profile_card_offers_switch_edit_and_logout(companies: CompanySwitchPage) -> None:
    companies.open_profile_card()

    companies.expect_profile_card_actions()


def test_switch_button_opens_the_organisation_list(companies: CompanySwitchPage) -> None:
    active_company = companies.stored_company_name()

    companies.open_from_profile_card()

    companies.expect_organisation_listed(active_company)


def test_search_keeps_the_active_company_listed(companies: CompanySwitchPage) -> None:
    active_company = companies.stored_company_name()
    companies.open()

    companies.search(active_company)

    companies.expect_organisation_listed(active_company)


def test_search_with_no_match_hides_the_active_company(companies: CompanySwitchPage) -> None:
    active_company = companies.stored_company_name()
    companies.open()

    companies.search(NO_SUCH_ORGANISATION)

    companies.expect_organisation_not_listed(active_company)
