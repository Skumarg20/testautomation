"""J22 dashboard period picker and refresh (specs/dashboard.md).

The chosen period is kept for the login, so these tests share one worker and choose the old one again.
"""

from datetime import date

import pytest

from pages.accounting.entry_date import format_for_app
from pages.dashboard.figures import DashboardFigures
from pages.dashboard.period_filter import Period, PeriodFilter

pytestmark = [pytest.mark.p2, pytest.mark.journey("dashboard"), pytest.mark.xdist_group("dashboard-period")]


def test_picker_offers_predefined_periods_and_a_custom_range(period_filter: PeriodFilter) -> None:
    """DB-03."""
    period_filter.open_menu()

    assert period_filter.offered_periods() == [period.value for period in Period]
    period_filter.expect_custom_range_offered()


def test_choosing_a_period_relabels_the_picker(period_filter: PeriodFilter) -> None:
    """DB-04: the figures are recalculated for the period (waited for inside `choose`)."""
    period_filter.choose(Period.TODAY)

    period_filter.expect_label(Period.TODAY.value)


def test_chosen_period_is_kept_when_the_dashboard_is_opened_again(
    period_filter: PeriodFilter, figures: DashboardFigures
) -> None:
    """DB-05."""
    period_filter.choose(Period.THIS_WEEK)

    figures.open()

    period_filter.expect_label(Period.THIS_WEEK.value)


def test_refresh_moves_last_sync_to_today(figures: DashboardFigures) -> None:
    """DB-06: the first paint shows the last sync; Refresh Dashboard recalculates now."""
    figures.refresh()

    assert figures.last_sync_day() == format_for_app(date.today())


def test_custom_from_date_keeps_the_day_typed_in_app_format(period_filter: PeriodFilter) -> None:
    """DB-13 (MB-024396 "date filter is not working"): the app shows dates as dd-mm-yyyy, so a typed
    dd-mm-yyyy From date must stay the same day once the box is left."""
    first_of_this_month = format_for_app(date.today().replace(day=1))
    period_filter.open_menu()

    period_filter.type_custom_from(first_of_this_month)

    period_filter.expect_custom_from(first_of_this_month)
