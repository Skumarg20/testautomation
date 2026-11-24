"""Holding a Sale Bill Setting for a test, skipping (with the reason) when the tenant does not offer the
option."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.checklist.sale_setting import OptionMissingError, SelectSetting, setting_held
from pages.settings.control_room import DateBilling, YesNo


@contextmanager
def held_or_skip(bill: ChecklistBill, setting: SelectSetting, wanted: str) -> Iterator[str]:
    """Like `setting_held`, but a missing option skips the test: the options come from the API."""
    try:
        with setting_held(bill, setting, wanted) as original:
            yield original
    except OptionMissingError as missing:
        pytest.skip(str(missing))


HoldDateBilling = Callable[[DateBilling, YesNo], None]
