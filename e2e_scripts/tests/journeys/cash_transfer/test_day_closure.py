"""J29 day closure, read only (specs/cash-transfer-day-closure.md, scenarios DC-*).

Closing a day is tenant-wide and has no undo, and the Daily Cashbook is off on this tenant
(NEEDS DECISION 1 in the spec), so these tests only open screens and write nothing.
"""

from datetime import date

import pytest
from playwright.sync_api import Page, expect

from pages.accounting.entry_date import format_for_app
from pages.cash_transfer.close_billing_day_page import CloseBillingDayPage, DailyCashbookScreen

pytestmark = [pytest.mark.p2, pytest.mark.journey("cash-transfer-day-closure")]

DAILY_CASHBOOK_ROUTES = ("/openclosecashbook", "/stopbilling", "/cashTransfer", "/dayclosureapproval")


def test_close_billing_day_opens_on_today(garments_page: Page) -> None:
    """DC-06: the closing date and both ends of the date range default to today."""
    screen = CloseBillingDayPage(garments_page)
    today = format_for_app(date.today())

    screen.open()

    assert screen.closing_date() == today
    assert screen.date_range() == (today, today)
    expect(screen.approvals_button).to_be_visible()


@pytest.mark.parametrize("path", DAILY_CASHBOOK_ROUTES)
def test_daily_cashbook_screen_is_not_authorized_while_the_setting_is_off(
    garments_page: Page, path: str
) -> None:
    """DC-01: without Control Room "Daily Cashbook" = Yes, even the admin gets the not-authorized page."""
    screen = DailyCashbookScreen(garments_page)

    screen.open(path)

    expect(screen.not_authorized_message).to_be_visible()
