"""The renewal order summary at /upgradesubscription: the current plan's yearly line (read only)."""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.subscription.rupees import rupees_in

ORDER_TIMEOUT_MS = 60_000
PLAN_ROW_INDEX = 0
PRINTED_AMOUNT = re.compile(r"^[\d,]+\.\d{2}$")


@dataclass(frozen=True)
class PlanLine:
    plan: str
    billing_cycle: str
    amount: Decimal


class RenewalOrderSummary(BasePage):
    PATH = "/upgradesubscription"

    def open(self) -> None:
        self.goto(self.PATH, ORDER_TIMEOUT_MS)
        expect(self._body_rows.first).to_be_visible(timeout=ORDER_TIMEOUT_MS)

    def plan_line(self) -> PlanLine:
        """The first row is the plan itself, printed as "<plan>" over "<billing cycle>" in one cell."""
        cells = self._body_rows.nth(PLAN_ROW_INDEX).get_by_role("cell")
        expect(cells.last).to_have_text(PRINTED_AMOUNT, timeout=ORDER_TIMEOUT_MS)
        plan, cycle = cells.first.inner_text().strip().splitlines()
        return PlanLine(plan.strip(), cycle.strip(), rupees_in(cells.last.inner_text()))

    @property
    def _body_rows(self) -> Locator:
        return self.page.get_by_role("row").filter(has=self.page.get_by_role("cell"))
