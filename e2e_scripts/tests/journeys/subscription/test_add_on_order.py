"""J34 add-ons: an add-on is charged pro rata to the plan's Next Due Date, plus 18% tax.

Plan: specs/subscription-status.md (SS-05, SS-11). Nothing is ordered: units are typed, the browser
computes the totals, and Proceed / Apply are never clicked.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest

from pages.subscription.add_on_order import AddOnOrder
from test_data.app_clock import app_today

pytestmark = [pytest.mark.p2, pytest.mark.journey("subscription-status")]

USER_ADD_ON = "USER"
UNITS = 2
DAYS_IN_BILLING_YEAR = 365
TAX_RATE = Decimal("0.18")
PAISE = Decimal("0.01")


def test_add_on_line_total_is_pro_rated_to_next_due_date(
    next_due_date: date, add_on_order: AddOnOrder
) -> None:
    charge = pro_rated_charge(add_on_order, next_due_date)

    add_on_order.enter_units(USER_ADD_ON, str(UNITS))

    add_on_order.expect_line_charged(USER_ADD_ON)
    assert add_on_order.line_total(USER_ADD_ON) == to_paise(charge)


def test_order_summary_adds_18_percent_tax(next_due_date: date, add_on_order: AddOnOrder) -> None:
    charge = pro_rated_charge(add_on_order, next_due_date)

    add_on_order.enter_units(USER_ADD_ON, str(UNITS))

    add_on_order.expect_line_charged(USER_ADD_ON)
    summary = add_on_order.summary()
    assert summary.add_ons == to_paise(charge)
    assert summary.tax == to_paise(charge * TAX_RATE)
    assert summary.total == to_paise(charge * (1 + TAX_RATE))
    add_on_order.expect_proceed_offered()


def test_negative_units_cost_nothing(add_on_order: AddOnOrder) -> None:
    add_on_order.enter_units(USER_ADD_ON, "-1")

    add_on_order.expect_line_free(USER_ADD_ON)
    assert add_on_order.summary().total == 0


def pro_rated_charge(add_on_order: AddOnOrder, due_on: date) -> Decimal:
    """UNITS of the add-on for the days left until the due date, unrounded (the app rounds each figure)."""
    days_left = (due_on - app_today()).days
    return UNITS * add_on_order.unit_price(USER_ADD_ON) * days_left / DAYS_IN_BILLING_YEAR


def to_paise(amount: Decimal) -> Decimal:
    return amount.quantize(PAISE, rounding=ROUND_HALF_UP)
