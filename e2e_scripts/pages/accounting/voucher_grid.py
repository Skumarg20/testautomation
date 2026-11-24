"""The entry grid of an accounting voucher. Cells are addressed by ag-Grid row id and column id."""

from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import Locator

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

Column = Literal["ledgerLinkID", "entryDate", "drAmount", "crAmount", "voucherNo", "creditOrDebit"]
INPUT_LOOKUP_MS = 2_000


@dataclass(frozen=True)
class CellRef:
    row: int
    column: Column


class VoucherGrid(BasePage):
    def cell(self, ref: CellRef) -> Locator:
        # Why CSS: ag-Grid exposes only row-id and col-id; the first body container holds the entry rows.
        body = self.page.locator('[ref="eBodyContainer"]').first
        return body.locator(f'[row-id="{ref.row}"] [col-id="{ref.column}"]')

    def cell_input(self, ref: CellRef) -> Locator:
        return self.cell(ref).locator("input")

    def type_into(self, ref: CellRef, text: str) -> None:
        """Opens the cell editor if needed, types the text and confirms with Enter."""
        editor = self.cell_input(ref)
        if not appears_within(editor, INPUT_LOOKUP_MS):
            self.cell(ref).click()
        editor.press_sequentially(text)
        editor.press("Enter")
