"""J21 per-user data across companies (specs/notifications-export.md, NE-42). The SMS log
(`GetSmsHistoryByuserID`) belongs to the user and the bell's feed is Marg-wide, so both must be the same in
the garments and the pharma company. The chemist login is switched and put back in garments afterwards."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.notifications_export.notification_feed import NotificationFeed
from pages.notifications_export.sms_notification_page import SmsNotificationPage

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("notifications-export"),
    pytest.mark.xdist_group("chemist-tenant"),
]


SwitchToPharma = Callable[[], None]


@pytest.fixture
def switch_to_pharma(journey_page: Page) -> Iterator[SwitchToPharma]:
    """Skips unless the chemist login also has the pharma company; yields the switch to it and puts the
    login back in garments afterwards."""
    companies = CompanySwitchPage(journey_page)
    companies.open()
    try:
        companies.expect_organisation_listed(PHARMA_COMPANY)
    except AssertionError:
        pytest.skip(f"NE-42: needs a second company ({PHARMA_COMPANY}) on the chemist login")
    DashboardPage(journey_page).open()

    def switch() -> None:
        companies.ensure_company(PHARMA_COMPANY)

    yield switch
    DashboardPage(journey_page).open()
    companies.ensure_company(GARMENTS_COMPANY)


def _sms_log(page: Page) -> list[str]:
    report = SmsNotificationPage(page)
    report.open()
    return report.logged_messages()


def test_sms_log_is_the_same_in_both_companies(journey_page: Page, switch_to_pharma: SwitchToPharma) -> None:
    """NE-42: the log is the user's; switching company neither hides nor adds messages."""
    in_garments = _sms_log(journey_page)
    DashboardPage(journey_page).open()
    switch_to_pharma()

    in_pharma = _sms_log(journey_page)

    assert in_pharma == in_garments


def test_bell_feed_is_the_same_in_both_companies(
    journey_page: Page, switch_to_pharma: SwitchToPharma
) -> None:
    """NE-42: the bell's feed is Marg-wide, not the company's. The switch ends on the new company's
    dashboard, which loads the feed again."""
    feed = NotificationFeed(journey_page)
    in_garments = feed.live_items_while(DashboardPage(journey_page).open)

    in_pharma = feed.live_items_while(switch_to_pharma)

    assert in_pharma == in_garments
