"""The dashboard period picker (top right): predefined ranges and a custom From/To range with Apply.

The choice is kept for the login after a reload, so tests that change it choose the old one again.
"""

import re
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.dashboard.figures import DashboardFigures

PICKER_TIMEOUT_MS = 60_000
CUSTOM_RANGE = r"\d{2}-\d{2}-\d{4} To \d{2}-\d{2}-\d{4}"


class Period(Enum):
    TODAY = "Today"
    YESTERDAY = "Yesterday"
    THIS_WEEK = "This Week"
    LAST_7_DAYS = "Last 7 Days"
    THIS_MONTH = "This Month"
    PREVIOUS_MONTH = "Previous Month"
    LAST_30_DAYS = "Last 30 Days"


DEFAULT_PERIOD = Period.LAST_30_DAYS
PREDEFINED_LABELS = "|".join(re.escape(period.value) for period in Period)
PICKER_LABEL = re.compile(f"^({PREDEFINED_LABELS}|{CUSTOM_RANGE})$")


class PeriodFilter(BasePage):
    def current_period(self) -> Period:
        """The predefined period shown; a custom range counts as the default (the app's first choice)."""
        label = self.label()
        return Period(label) if label in {period.value for period in Period} else DEFAULT_PERIOD

    def label(self) -> str:
        expect(self._picker).to_be_visible(timeout=PICKER_TIMEOUT_MS)
        return self._picker.inner_text().strip()

    def choose(self, period: Period) -> None:
        self.open_menu()
        DashboardFigures(self.page).recalculate_after(self._option(period).click)
        expect(self._picker).to_have_text(period.value)

    def open_menu(self) -> None:
        self._picker.click()
        expect(self._apply).to_be_visible()

    def offered_periods(self) -> list[str]:
        """The predefined options shown in the open menu, in the order of `Period`."""
        names = (self._option_link(period.value) for period in Period)
        return [period.value for period, link in zip(Period, names, strict=True) if link.is_visible()]

    def type_custom_from(self, day: str) -> None:
        """Types a dd-mm-yyyy date into the custom From box and leaves it, as a user tabbing on."""
        self._custom_from.fill(day)
        self._custom_from.press("Tab")

    def expect_custom_from(self, day: str) -> None:
        expect(self._custom_from).to_have_value(day)

    def expect_custom_range_offered(self) -> None:
        expect(self._custom_from).to_be_visible()
        expect(self._custom_to).to_be_visible()
        expect(self._apply).to_be_visible()

    def expect_label(self, label: str) -> None:
        expect(self._picker).to_have_text(label, timeout=PICKER_TIMEOUT_MS)

    @property
    def _main(self) -> Locator:
        return self.page.get_by_role("main")

    @property
    def _picker(self) -> Locator:
        return self._main.get_by_role("button", name=PICKER_LABEL)

    def _option(self, period: Period) -> Locator:
        return self._option_link(period.value)

    def _option_link(self, label: str) -> Locator:
        return self._main.get_by_role("link", name=label, exact=True)

    @property
    def _custom_from(self) -> Locator:
        # The open menu holds the only two text boxes of the dashboard: From, then To.
        return self._main.get_by_role("textbox").nth(0)

    @property
    def _custom_to(self) -> Locator:
        return self._main.get_by_role("textbox").nth(1)

    @property
    def _apply(self) -> Locator:
        return self._main.get_by_role("button", name="Apply", exact=True)
