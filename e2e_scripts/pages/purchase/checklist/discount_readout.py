"""The "Total Disc" figure in the totals panel of an open purchase bill (InvoiceFooter reads it privately)."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

TOTAL_TIMEOUT_MS = 15_000


class DiscountReadout(BasePage):
    def expect_total(self, amount: Decimal) -> None:
        """Waits until the panel shows `amount` (the app may show two or three decimals)."""
        expect(self._panel).to_have_text(
            re.compile(rf"Total Disc\D*{_amount_pattern(amount)}\s*$"), timeout=TOTAL_TIMEOUT_MS
        )

    @property
    def _panel(self) -> Locator:
        # Why CSS: the totals panel rows are spans with a class and no role or label.
        return self.page.locator("span.rb").filter(has_text="Total Disc").first


def _amount_pattern(amount: Decimal) -> str:
    whole, _, fraction = f"{amount:f}".partition(".")
    grouped = ",?".join(whole)
    return rf"{grouped}(\.0+)?" if not fraction.strip("0") else rf"{grouped}\.{fraction.rstrip('0')}0*"
