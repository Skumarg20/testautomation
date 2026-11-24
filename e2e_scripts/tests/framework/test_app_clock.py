from datetime import date, datetime, timezone

import pytest

from test_data.app_clock import app_date_at

pytestmark = pytest.mark.framework


def test_late_evening_utc_is_already_the_next_day_in_the_app() -> None:
    assert app_date_at(datetime(2026, 10, 12, 19, 0, tzinfo=timezone.utc)) == date(2026, 10, 13)


def test_just_before_midnight_ist_is_still_the_same_day() -> None:
    assert app_date_at(datetime(2026, 10, 12, 18, 29, tzinfo=timezone.utc)) == date(2026, 10, 12)
