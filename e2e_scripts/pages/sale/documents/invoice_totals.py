"""The invoice-value check every sale document makes before it is saved."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.document_requests import last_number, parse_decimal
from pages.sale.documents.item_grid import DocumentItemGrid
from pages.sale.documents.screen import is_shown_within

CENTS = Decimal("0.01")
FIGURE_WAIT_MS = 2_000
GROSS_TIMEOUT_MS = 15_000
TAXES = ("CGST", "SGST", "IGST")


class InvoiceTotalMismatchError(AssertionError):
    def __init__(self, calculated: Decimal, displayed: Decimal) -> None:
        super().__init__(f"Invoice value mismatch: calculated {calculated}, displayed {displayed}")


class InvoiceTotals(BasePage):
    def expect_consistent(self, *, has_lines: bool) -> None:
        """Gross - total discount + tax + round off must equal the invoice value shown.

        Tax is CGST + SGST within the state and IGST between states; a tax the panel does not show is zero.
        Only a document with no lines skips the check; the caller says so, never a figure on screen.
        """
        if not has_lines:
            return
        gross = self._gross_total()
        displayed = self._invoice_value()
        tax = sum((self._tax(name) for name in TAXES), Decimal(0))
        calculated = gross - self._total_discount() + tax + self._round_off()
        if calculated.quantize(CENTS) != displayed.quantize(CENTS):
            raise InvoiceTotalMismatchError(calculated, displayed)

    def _gross_total(self) -> Decimal:
        """The totals row must show: a missing one would quietly switch the invoice check off."""
        cell = DocumentItemGrid(self.page).totals_amount()
        expect(cell).to_have_text(re.compile(r"\d"), timeout=GROSS_TIMEOUT_MS)
        return parse_decimal(cell.inner_text())

    def _tax(self, name: str) -> Decimal:
        # The tax figure sits in the box next to its name; both are plain divs.
        amount = self.page.locator(f'div:text-is("{name}") + div span.blueColor')
        return self._figure(amount)

    def _total_discount(self) -> Decimal:
        text = self.page.locator("span.rb", has_text="Total Disc")
        return last_number(text.first.inner_text()) if is_shown_within(text, FIGURE_WAIT_MS) else Decimal(0)

    def _round_off(self) -> Decimal:
        row = self.page.get_by_role("row").filter(has=self.page.get_by_text("Round Off", exact=True))
        return self._figure(row.locator('[col-id="amount"]'))

    def _invoice_value(self) -> Decimal:
        value = self.page.locator(".bill-value-text").first
        expect(value).to_be_visible()
        return last_number(value.inner_text())

    @staticmethod
    def _figure(locator: Locator) -> Decimal:
        if not is_shown_within(locator, FIGURE_WAIT_MS):
            return Decimal(0)
        return parse_decimal(locator.first.inner_text())
