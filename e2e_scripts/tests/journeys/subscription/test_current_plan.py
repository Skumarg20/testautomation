"""J34 current plan: plan, price and dates are shown, consistent with each other and with the renewal order.

Plan: specs/subscription-status.md (SS-02, SS-03, SS-07, SS-12). Read only; no value is hardcoded.
"""

import re
from datetime import date

import pytest

from pages.subscription.current_plan import CurrentPlanCard
from pages.subscription.renewal_order import RenewalOrderSummary
from test_data.app_clock import app_today

pytestmark = [pytest.mark.p2, pytest.mark.journey("subscription-status")]

YEARLY = "Yearly"
TWO_COUNTS = re.compile(r"^\d+/\d+$")


def test_current_plan_shows_name_price_and_dates(current_plan: CurrentPlanCard) -> None:
    assert current_plan.plan_name()
    assert current_plan.price() > 0
    assert current_plan.subscription_date() <= current_plan.activation_date() <= current_plan.next_due_date()


def test_next_due_date_is_one_billing_year_after_subscription(current_plan: CurrentPlanCard) -> None:
    subscribed_on, due_on = current_plan.subscription_date(), current_plan.next_due_date()
    renewal = RenewalOrderSummary(current_plan.page)

    renewal.open()

    assert renewal.plan_line().billing_cycle == YEARLY
    assert due_on == one_year_after(subscribed_on)


def test_active_plan_is_due_in_the_future(current_plan: CurrentPlanCard) -> None:
    assert current_plan.next_due_date() > app_today()


def test_current_plan_matches_renewal_order_summary(current_plan: CurrentPlanCard) -> None:
    plan, price = current_plan.plan_name(), current_plan.price()
    renewal = RenewalOrderSummary(current_plan.page)

    renewal.open()

    assert (renewal.plan_line().plan, renewal.plan_line().amount) == (plan, price)


def test_add_on_stats_show_two_counts(current_plan: CurrentPlanCard) -> None:
    stats = current_plan.add_on_stats()

    assert {"Users", "GSTIN", "Organisation"} <= stats.keys()
    assert all(TWO_COUNTS.match(counts) for counts in stats.values()), stats


def one_year_after(day: date) -> date:
    """The same day a year later; 29 February falls back to 28 February."""
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return day.replace(year=day.year + 1, day=28)
