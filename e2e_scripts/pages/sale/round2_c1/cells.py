"""Reads and checks single cells of the sale grid by col-id, scrolling to a far-right column when needed."""

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.sale.documents.item_grid import DocumentItemGrid

FREE = "free"
DISCOUNT_1 = "discount1"
RATE = "salePurchaseRate"
UNIT_2 = "unitFromEnteredValue"
UNIT_1 = "unitToEnteredValue"
QUANTITY = "quantity"
CELL_WAIT_MS = 1_500
CHECK_TIMEOUT_MS = 15_000
SCROLL_RIGHT = "viewports => viewports.forEach(el => { el.scrollLeft = el.scrollWidth; })"
SCROLL_LEFT = "viewports => viewports.forEach(el => { el.scrollLeft = 0; })"


def number_text(value: Decimal) -> re.Pattern[str]:
    """How a cell may show `value`: thousands commas and trailing zeros are optional."""
    whole, _, fraction = f"{value:f}".partition(".")
    digits = ",?".join(whole)
    tail = rf"\.{fraction.rstrip('0')}0*" if fraction.strip("0") else r"(\.0+)?"
    return re.compile(rf"^\s*{digits}{tail}\s*$")


class GridCells(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._grid = DocumentItemGrid(page)

    def expect_value(self, row: int, column: str, expected: Decimal) -> None:
        cell = self._grid.cell(row, column)
        if not appears_within(cell, CELL_WAIT_MS):
            self.page.locator(".ag-body-viewport").evaluate_all(SCROLL_RIGHT)
        expect(cell).to_have_text(number_text(expected), timeout=CHECK_TIMEOUT_MS)
        self.page.locator(".ag-body-viewport").evaluate_all(SCROLL_LEFT)

    def expect_column_shown(self, row: int, column: str) -> None:
        expect(self._grid.cell(row, column)).to_be_visible(timeout=CHECK_TIMEOUT_MS)

    def type_into(self, row: int, column: str, value: Decimal) -> None:
        cell = self._grid.cell(row, column)
        cell.click()
        editor = cell.locator("input")
        editor.press("Control+A")
        editor.press_sequentially(f"{value:f}")
        editor.press("Enter")

    def expect_empty_or_zero(self, row: int, column: str) -> None:
        cell = self._grid.cell(row, column)
        if not appears_within(cell, CELL_WAIT_MS):
            self.page.locator(".ag-body-viewport").evaluate_all(SCROLL_RIGHT)
        expect(cell).to_have_text(re.compile(r"^\s*(0(\.0+)?)?\s*$"), timeout=CHECK_TIMEOUT_MS)
        self.page.locator(".ag-body-viewport").evaluate_all(SCROLL_LEFT)


INVOICE_CLOSE_TO = """
([expected, tolerance]) => {
    const node = [...document.querySelectorAll('*')].filter(
        e => e.children.length === 0 || e.childElementCount < 3).find(e => /Invoice
        Value\\s*:/.test(e.textContent || ''));
    if (!node) return false;
    const shown = /Invoice Value\\s*:\\s*[^\\d-]*(-?[\\d.,]+)/.exec(node.textContent);
    return shown !== null && Math.abs(parseFloat(shown[1].replace(/,/g, '')) - expected) <= tolerance;
}
"""


def expect_invoice_close_to(page: Page, expected: Decimal, tolerance: Decimal) -> None:
    """Waits until the "Invoice Value" figure is within `tolerance` of `expected` (rounded invoices
    differ by < 1)."""
    page.wait_for_function(
        INVOICE_CLOSE_TO, arg=[float(expected), float(tolerance)], timeout=CHECK_TIMEOUT_MS
    )
