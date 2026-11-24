"""Sale checklist rows 4 and 5: the bill date is governed by the Sale Back Date / Future Date Billing
switches.

Warning texts: global.ts:19306 "Back Date Billing Not Allowed", global.ts:19761 "Future Date Billing Not
Allowed". Handler: `processout.transaction.component.ts:1791-1850` (onDateKeyUp) with
`dataCalculation.backDate` / `futureDate`. A1 owns the save-side rule (Ajay rows 150 and 152); these tests
assert the cursor and the warning only, and never save."""

from datetime import date, timedelta

import pytest

from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.checklist.focus import BILL_DATE, IN_A_WINDOW, PARTY
from pages.sale.checklist.holds import HoldDateBilling
from pages.settings.control_room import DateBilling

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

BACK_DATE: DateBilling = "Sale BackDate Billing"
FUTURE_DATE: DateBilling = "Sale Future Date Billing"
YESTERDAY = date.today() - timedelta(days=1)
TOMORROW = date.today() + timedelta(days=1)


def test_back_date_is_refused_and_the_cursor_stays_on_the_date_when_back_billing_is_off(
    hold_date_billing: HoldDateBilling,
    screen: ChecklistBill,
) -> None:
    """Row 4: with Sale BackDate Billing = No a past date gets the warning and the date keeps the cursor
    (onDateKeyUp returns the BackDate alert before it moves to the party)."""
    hold_date_billing(BACK_DATE, "No")
    hold_date_billing(FUTURE_DATE, "Yes")  # keeps the bill date reachable (PO:1050-1062)
    screen.open_new()
    screen.focus.expect_at(BILL_DATE)

    screen.enter_date(YESTERDAY)

    screen.expect_warning()
    assert screen.focus.is_at(BILL_DATE)


def test_future_date_is_refused_and_the_cursor_stays_on_the_date_when_future_billing_is_off(
    hold_date_billing: HoldDateBilling,
    screen: ChecklistBill,
) -> None:
    """Row 4: the same for Sale Future Date Billing = No and a date after today."""
    hold_date_billing(FUTURE_DATE, "No")
    hold_date_billing(BACK_DATE, "Yes")
    screen.open_new()
    screen.focus.expect_at(BILL_DATE)

    screen.enter_date(TOMORROW)

    screen.expect_warning()
    assert screen.focus.is_at(BILL_DATE)


def test_back_date_is_accepted_and_the_cursor_moves_on_when_back_billing_is_on(
    hold_date_billing: HoldDateBilling,
    screen: ChecklistBill,
) -> None:
    """Row 5: with Sale BackDate Billing = Yes a past date is taken (only the "date differs from your
    computer date" notice shows, PO:1813) and the cursor goes on to the party."""
    hold_date_billing(BACK_DATE, "Yes")
    screen.open_new()
    screen.focus.expect_at(BILL_DATE)

    screen.enter_date(YESTERDAY)

    screen.focus.expect_at(PARTY, IN_A_WINDOW)
