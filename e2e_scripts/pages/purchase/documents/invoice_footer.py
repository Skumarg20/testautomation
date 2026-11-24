"""The bottom of a purchase document: bill discount, tax and the invoice value the app calculates."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.documents.entry_grid import EntryGrid
from pages.purchase.documents.feedback import appears_within
from pages.purchase.documents.fields import labelled_input
from test_data.money import parse_amount, to_money

NUMBER = re.compile(r"\d+\.?\d*")
ITEM_DETAILS_TIMEOUT_MS = 2_000
OPTIONAL_TIMEOUT_MS = 1_000
VALUE_TIMEOUT_MS = 10_000
ROUND_OFF_LABEL = "Round Off"
DISCOUNT_LABEL = "Bill Discount"
INPUT_TAXES = ("CGST", "SGST", "IGST")


class InvoiceMismatchError(AssertionError):
    def __init__(self, calculated: Decimal, displayed: Decimal) -> None:
        super().__init__(f"Invoice value mismatch: calculated {calculated}, displayed {displayed}")


class InvoiceFooter(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._grid = EntryGrid(page)

    def enter_bill_discount(self, discount: Decimal) -> None:
        self._close_item_details()
        # A click on the page body takes focus off the grid so that the discount field gets the next click.
        self.page.locator("body").click()
        field = self.bill_discount_field
        field.click()
        field.press_sequentially(str(discount))
        field.press("Enter")

    def expect_invoice_value_consistent(self, *, has_lines: bool = True) -> None:
        """Gross - total discount + input tax + round off must equal the invoice value shown.

        Input tax is CGST + SGST within the state and IGST between states; a tax not shown is zero. The
        invoice value is read first, so the optional tax lookups run against a panel that has rendered.
        Only a document with no lines skips the check; the caller says so, never a figure on screen.
        """
        if not has_lines:
            return
        gross = self._grid.gross_amount()
        displayed = self._invoice_value()
        tax = sum((self._input_tax(name) for name in INPUT_TAXES), Decimal(0))
        calculated = gross - self._total_discount() + tax + self._round_off()
        if to_money(calculated) != to_money(displayed):
            raise InvoiceMismatchError(calculated, displayed)

    @property
    def bill_discount_field(self) -> Locator:
        return labelled_input(self.page, DISCOUNT_LABEL)

    @property
    def bill_value_field(self) -> Locator:
        # The id ends in the tab number, and the newest tab is last.
        return self.page.locator("[id^=txtbillValue]").last

    def _close_item_details(self) -> None:
        # The item-details panel is a draggable div; its close mark is a bare "×" span in the header.
        panel = self.page.locator("div.dragPopuppp.unselectable").filter(
            has=self.page.locator("item-details")
        )
        if appears_within(panel.locator("div.pageHeader h5"), ITEM_DETAILS_TIMEOUT_MS):
            self.page.locator("div.pageHeader").get_by_text("×").click()

    def _invoice_value(self) -> Decimal:
        value = self.page.locator("div.pr-0.bill-value-text")
        expect(value).to_be_visible(timeout=VALUE_TIMEOUT_MS)
        return _last_number(value.inner_text())

    def _total_discount(self) -> Decimal:
        return _last_number(self.page.locator("span.rb").filter(has_text="Total Disc").first.inner_text())

    def _input_tax(self, tax: str) -> Decimal:
        # The tax name and its amount sit in neighbouring divs of the totals panel.
        amount = self.page.locator(
            f"xpath=//div[normalize-space()='{tax} Input']/following-sibling::div[1]"
            "//span[contains(@class,'blueColor')]"
        )
        if not appears_within(amount.first, OPTIONAL_TIMEOUT_MS):
            return Decimal(0)
        return parse_amount(amount.first.inner_text())

    def _round_off(self) -> Decimal:
        row = (
            self.page.get_by_role("row").filter(has=self.page.get_by_text(ROUND_OFF_LABEL, exact=True)).first
        )
        amount = row.locator('[col-id="amount"]')
        if not appears_within(amount, OPTIONAL_TIMEOUT_MS):
            return Decimal(0)
        text = amount.inner_text().strip()
        return parse_amount(text) if text else Decimal(0)


def _last_number(text: str) -> Decimal:
    numbers = NUMBER.findall(text.replace(",", ""))
    return Decimal(numbers[-1]) if numbers else Decimal(0)
