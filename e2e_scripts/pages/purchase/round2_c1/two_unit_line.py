"""The Unit-2 / Unit-1 / Free cells of a purchase line when Multi Unit is on.

col-ids `unitFromEnteredValue` (Unit-2, the bigger unit) and `unitToEnteredValue` (Unit-1, the base
unit) replace
the Quantity column (transactionin.component.ts:5616; header text "Unit-2" / "Unit-1" from
processout.transaction.component.ts:1721-1722); the stored quantity is unit 2 x conversion + unit 1
(transactionin.component.ts:4080). The free quantity goes into the smaller unit (sheet row 23).
"""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.round2_c1.cells import number_text

UNIT_2 = "unitFromEnteredValue"
UNIT_1 = "unitToEnteredValue"
FREE = "free"
CELL_TIMEOUT_MS = 15_000


class TwoUnitLine(BasePage):
    def enter(self, column: str, value: Decimal) -> None:
        cell = self._cell(column)
        cell.click()
        editor = cell.locator("input")
        editor.press("Control+A")
        editor.press_sequentially(f"{value:f}")
        editor.press("Enter")

    def expect_both_unit_cells(self) -> None:
        expect(self._cell(UNIT_2)).to_be_visible(timeout=CELL_TIMEOUT_MS)
        expect(self._cell(UNIT_1)).to_be_visible(timeout=CELL_TIMEOUT_MS)

    def expect_headers(self) -> None:
        expect(self.page.get_by_role("columnheader", name="Unit-2")).to_be_visible(timeout=CELL_TIMEOUT_MS)
        expect(self.page.get_by_role("columnheader", name="Unit-1")).to_be_visible(timeout=CELL_TIMEOUT_MS)

    def expect_value(self, column: str, expected: Decimal) -> None:
        expect(self._cell(column)).to_have_text(number_text(expected), timeout=CELL_TIMEOUT_MS)

    def _cell(self, column: str) -> Locator:
        # Why CSS: ag-Grid cells carry only row-id and col-id (as in EntryGrid._cell).
        return self.page.locator(".ag-body-container").first.locator(f'[row-id="0"] [col-id="{column}"]')
