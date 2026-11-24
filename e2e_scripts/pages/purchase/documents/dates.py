"""Dates and unique labels. Excel stores dates as day numbers; the sheets say "today" or give one."""

import secrets
from datetime import date, datetime
from decimal import Decimal
from itertools import count

EXCEL_EPOCH = date(1899, 12, 30)
TODAY_WORD = "today"
ENTRY_DATE_FORMAT = "%d-%m-%Y"
EXPIRY_FORMAT = "%m-%Y"
LABEL_FORMAT = "%y%m%d%H%M%S"
LABEL_SUFFIXES = 100_000
# A random start per process (xdist worker) plus a counter: labels made in the same second differ within
# one worker always, and across workers unless two random starts land within a few labels of each other.
_PROCESS_START = secrets.randbelow(LABEL_SUFFIXES)
_SERIAL = count()


def todays_serial() -> int:
    return (date.today() - EXCEL_EPOCH).days


def resolve_date(raw: str) -> int:
    """The one place where "today" becomes a day number."""
    return todays_serial() if raw == TODAY_WORD else int(Decimal(raw))


def entry_date_text(serial: int) -> str:
    return _as_date(serial).strftime(ENTRY_DATE_FORMAT)


def expiry_text(serial: int | None) -> str:
    return "" if serial is None else _as_date(serial).strftime(EXPIRY_FORMAT)


def timestamp_label() -> str:
    """Document numbers and batch names: the current time to the second, as in the original, plus a
    suffix, so documents saved in the same second by parallel workers do not share a number or batch.
    Kept within the original's 19 characters."""
    suffix = (_PROCESS_START + next(_SERIAL)) % LABEL_SUFFIXES
    return f"{datetime.now().strftime(LABEL_FORMAT)}-{suffix:05d}"


def _as_date(serial: int) -> date:
    return date.fromordinal(EXCEL_EPOCH.toordinal() + serial)
