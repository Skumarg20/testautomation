"""The app's calendar date: the server dates vouchers and charges in IST, whatever the runner's clock says."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def app_date_at(moment: datetime) -> date:
    return moment.astimezone(APP_TIMEZONE).date()


def app_today() -> date:
    """Today as the app sees it; on a UTC runner after 18:30 this is already tomorrow's date."""
    return datetime.now(APP_TIMEZONE).date()
