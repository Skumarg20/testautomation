"""The Net Profit window (Alt+F10 on a sale bill): cost, value and profit of the selected line or the bill.

Component `childcomponents/netProfit.component.ts`: value = rate x quantity - discounts (less GST when the
bill is inclusive), cost = cost x (quantity + free), profit = value - cost, percentage = profit / cost x
100 (a zero cost counts as 1). The window's text is read, not its markup, because the template has no ids."""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.document_requests import parse_decimal

WINDOW_TIMEOUT_MS = 10_000
AMOUNT = r"(-?[\d,]+\.\d+)"


@dataclass(frozen=True)
class NetProfit:
    cost: Decimal
    value: Decimal
    profit: Decimal
    percentage: Decimal


class NetProfitWindow(BasePage):
    def open(self) -> None:
        self.page.keyboard.press("Alt+F10")
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def close(self) -> None:
        self.page.keyboard.press("Escape")
        expect(self._window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    def figures(self) -> NetProfit:
        text = self._window.inner_text()
        return NetProfit(
            cost=self._amount_after("Cost", text),
            value=self._amount_after("Value", text),
            profit=self._amount_after("Profit", text),
            percentage=self._percentage(text),
        )

    @staticmethod
    def _amount_after(label: str, text: str) -> Decimal:
        found = re.search(rf"{label}\s*:?[^\d-]*{AMOUNT}", text)
        if found is None:
            raise LookupError(f"The Net Profit window shows no '{label}' amount: {text!r}")
        return parse_decimal(found.group(1))

    @staticmethod
    def _percentage(text: str) -> Decimal:
        found = re.search(r"Net Profit\s*:?\s*(-?[\d.]+)\s*%", text)
        if found is None:
            raise LookupError(f"The Net Profit window shows no percentage: {text!r}")
        return parse_decimal(found.group(1))

    @property
    def _window(self) -> Locator:
        return self.page.locator("ngb-modal-window:not([aria-hidden='true'])").filter(has_text="Profit").last
