"""Control Room > Configure > "Multi Unit": the Yes/No row and its "Multi Unit Billing" window.

The row opens the window with its Configure button
(UtililityComponent/DynamicForm/form.component.ts:3391-3398,
title "Multi Unit Billing"); its controls are dynamic-form ids `ddl<bindCode>`: `ddl601` No. of unit required
(2-5, form.component.ts:709-716, field 2321), `ddl610` Stock show in unit (field 4002), `ddl608` Rate in unit
(field 2353; lookup 1289: 0 Unit1, 1 Unit2, 3 Ask). Option values are the lookup codes. The two-unit entry
needs 2321 = 2, 2303 = T and 4002 = 1 (Services/Helper.services.ts:10569-10584); the Unit-1 / Unit-2 cells
show only when the rate in unit is not Ask (processout.transaction.component.ts:6803-6820).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from playwright.sync_api import Locator, expect

from pages.settings.control_room import ControlRoom

ROW_TEXT = "Multi Unit"
WINDOW_TITLE = "Multi Unit Billing"
WINDOW_TIMEOUT_MS = 15_000
UNITS_FIELD = "#ddl601"
STOCK_UNIT_FIELD = "#ddl610"
RATE_UNIT_FIELD = "#ddl608"
YES = "Yes"
NO = "No"


@dataclass(frozen=True)
class MultiUnitValues:
    enabled: str
    units: str
    stock_unit: str
    rate_unit: str


TWO_UNITS = MultiUnitValues(YES, "2", "1", "0")


class MultiUnitSettings(ControlRoom):
    def current(self) -> MultiUnitValues:
        row = self._open_row()
        enabled = row.locator("select").locator("option:checked").inner_text().strip()
        row.get_by_role("button", name="Configure").click()
        window = self._window()
        values = MultiUnitValues(
            enabled,
            window.locator(UNITS_FIELD).input_value(),
            window.locator(STOCK_UNIT_FIELD).input_value(),
            window.locator(RATE_UNIT_FIELD).input_value(),
        )
        self.page.keyboard.press("Escape")
        self.page.keyboard.press("Escape")
        return values

    def apply(self, values: MultiUnitValues) -> None:
        row = self._open_row()
        row.locator("select").select_option(label=values.enabled)
        row.get_by_role("button", name="Configure").click()
        window = self._window()
        window.locator(UNITS_FIELD).fill(values.units)
        window.locator(STOCK_UNIT_FIELD).select_option(value=values.stock_unit)
        window.locator(RATE_UNIT_FIELD).select_option(value=values.rate_unit)
        self.page.keyboard.press("Escape")
        self.save_button.click()
        self.confirm_buttons.first.click()
        self.confirm_buttons.last.click()
        self.page.wait_for_load_state("load")

    def _open_row(self) -> Locator:
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(ROW_TEXT)
        return self.page.locator(".row.m-0", has_text=ROW_TEXT).first

    def _window(self) -> Locator:
        window = self.page.get_by_role("dialog").filter(has_text=WINDOW_TITLE)
        expect(window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        return window


@contextmanager
def multi_unit_held(settings: MultiUnitSettings, wanted: MultiUnitValues) -> Iterator[MultiUnitValues]:
    """Yields the original values; they are written back, and read again, afterwards."""
    original = settings.current()
    if original == wanted:
        yield original
        return
    try:
        settings.apply(wanted)
        yield original
    finally:
        settings.apply(original)
        if settings.current() != original:
            raise MultiUnitNotRestoredError(original)


class MultiUnitNotRestoredError(AssertionError):
    def __init__(self, original: MultiUnitValues) -> None:
        super().__init__(f"Multi Unit settings were not restored to {original}; put them back by hand")
