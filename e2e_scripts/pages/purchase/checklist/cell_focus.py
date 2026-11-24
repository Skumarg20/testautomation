"""Which grid cell of a purchase line holds the cursor (sheet rows 15, 25 and 28)."""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.purchase.documents.entry_grid import RATE
from pages.purchase.documents.feedback import appears_within

FOCUS_TIMEOUT_MS = 5_000
CELL_LOOKUP_MS = 1_000
DISCOUNT_1 = "discount1"


class CellFocus(BasePage):
    def expect_on_quantity(self, row: int) -> None:
        # The quantity editor has an id per row and no label (EntryGrid.type_quantity).
        expect(self.page.locator(f"#txt-quantity-{row}")).to_be_focused(timeout=FOCUS_TIMEOUT_MS)

    def expect_on_rate(self, row: int) -> None:
        expect(self._editor(row, RATE)).to_be_focused(timeout=FOCUS_TIMEOUT_MS)

    def expect_on_first_discount(self, row: int) -> None:
        expect(self._editor(row, DISCOUNT_1)).to_be_focused(timeout=FOCUS_TIMEOUT_MS)

    def first_discount_is_shown(self, row: int) -> bool:
        return appears_within(self._cell(row, DISCOUNT_1), CELL_LOOKUP_MS)

    def _editor(self, row: int, column: str) -> Locator:
        return self._cell(row, column).locator("input")

    def _cell(self, row: int, column: str) -> Locator:
        # Why CSS: ag-Grid cells carry only row-id and col-id attributes (as in EntryGrid._cell).
        return self.page.locator(".ag-body-container").first.locator(f'[row-id="{row}"] [col-id="{column}"]')
