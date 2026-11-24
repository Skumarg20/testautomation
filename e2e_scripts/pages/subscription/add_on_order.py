"""The Add On tab: units per add-on, the pro-rated line totals and the Order Summary. Nothing is ordered:
the totals are computed in the browser, and Proceed / Apply are never clicked."""

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.subscription.rupees import rupees_in

TABLE_TIMEOUT_MS = 30_000
UNIT_PRICE_CELL = 1
LINE_TOTAL_CELL = 3
NOTHING = "0.00"


@dataclass(frozen=True)
class OrderSummary:
    add_ons: Decimal
    tax: Decimal
    total: Decimal


class AddOnOrder(BasePage):
    def unit_price(self, add_on: str) -> Decimal:
        return rupees_in(self._cell(add_on, UNIT_PRICE_CELL).inner_text())

    def enter_units(self, add_on: str, units: str) -> None:
        field = self._row(add_on).get_by_role("textbox", name="No. of Units")
        field.fill(units)
        field.press("Tab")

    def expect_line_charged(self, add_on: str) -> None:
        expect(self._cell(add_on, LINE_TOTAL_CELL)).not_to_have_text(NOTHING)

    def expect_line_free(self, add_on: str) -> None:
        expect(self._cell(add_on, LINE_TOTAL_CELL)).to_have_text(NOTHING)

    def line_total(self, add_on: str) -> Decimal:
        return rupees_in(self._cell(add_on, LINE_TOTAL_CELL).inner_text())

    def summary(self) -> OrderSummary:
        return OrderSummary(
            add_ons=self._summary_amount("Add-Ons"),
            tax=self._summary_amount("Tax @18%"),
            total=self._summary_amount("Total"),
        )

    def expect_proceed_offered(self) -> None:
        expect(self.page.get_by_role("link", name="Proceed", exact=True)).to_be_visible()

    def _summary_amount(self, label: str) -> Decimal:
        line = self._summary.get_by_role("paragraph").filter(has_text=label)
        return rupees_in(line.inner_text().replace(label, "", 1))

    @property
    def _summary(self) -> Locator:
        return self.page.get_by_role("heading", name="Order Summary").locator("..")

    def _row(self, add_on: str) -> Locator:
        name_cell = self.page.get_by_role("cell", name=add_on, exact=True)
        row = self.page.get_by_role("row").filter(has=name_cell)
        expect(row).to_be_visible(timeout=TABLE_TIMEOUT_MS)
        return row

    def _cell(self, add_on: str, index: int) -> Locator:
        return self._row(add_on).get_by_role("cell").nth(index)
