"""The tax and discount figures a sale bill shows below the grid (the same panel `InvoiceTotals` reads)."""

from decimal import Decimal

from pages.base_page import BasePage
from pages.sale.documents.document_requests import last_number, parse_decimal
from pages.sale.documents.screen import is_shown_within

FIGURE_WAIT_MS = 2_000


class TaxPanel(BasePage):
    def tax(self, name: str) -> Decimal:
        """CGST, SGST, IGST or CESS as shown; zero when the bill does not show that tax."""
        # Why this shape: the figure sits in the box next to its name; both are plain divs.
        amount = self.page.locator(f'div:text-is("{name}") + div span.blueColor')
        if not is_shown_within(amount, FIGURE_WAIT_MS):
            return Decimal(0)
        return parse_decimal(amount.first.inner_text())

    def total_discount(self) -> Decimal:
        text = self.page.locator("span.rb", has_text="Total Disc")
        return last_number(text.first.inner_text()) if is_shown_within(text, FIGURE_WAIT_MS) else Decimal(0)
