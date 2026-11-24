"""The one place where an Excel "entry_date" value becomes a date and the text the app expects."""

from datetime import date, datetime

TODAY = "today"
SHEET_DATE_FORMAT = "%Y%m%d"
APP_DATE_FORMAT = "%d-%m-%Y"


def resolve_entry_date(raw: str) -> date:
    """ "today" means the current local date; anything else is a compact yyyymmdd date such as 20250101."""
    if raw == TODAY:
        return date.today()
    return datetime.strptime(raw, SHEET_DATE_FORMAT).date()


def format_for_app(day: date) -> str:
    return day.strftime(APP_DATE_FORMAT)


def is_today(day: date) -> bool:
    return day == date.today()
