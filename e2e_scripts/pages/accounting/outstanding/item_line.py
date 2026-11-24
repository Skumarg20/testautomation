"""One line of the 0% GST item on a sale bill or sale return, priced at the document's amount.

Live 2026-10-09: Enter in the product cell opens Select Item with its search box focused; typing the name
highlights the item row and Enter picks it. The exempt item has no variants, so it lands straight in the
grid with the Qty editor open (default 10); quantity and rate are then edited in their cells. The line
amount is checked before going on, so a wrong quantity cannot silently change the bill amount.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within, disappears_within
from pages.components.bill_totals import amount_pattern
from pages.sale.documents.document import SaleDocument

PRODUCT = "itemLinkID"
QUANTITY = "quantity"
RATE = "salePurchaseRate"
AMOUNT = "DisplayAmount"
WINDOW_TIMEOUT_MS = 15_000
SEARCH_RESULT_TIMEOUT_MS = 60_000
KEY_DELAY_MS = 100
PICK_ATTEMPTS = 3
PICK_ATTEMPT_MS = 8_000
EDITOR_LOOKUP_MS = 2_000
ONE = Decimal(1)
LINE = 0


class OneItemLine:
    def __init__(self, document: SaleDocument, item: str) -> None:
        self._document = document
        self._page = document.page
        self._item = item
        self._grid = document.grid

    def add(self, amount: Decimal) -> None:
        self._pick_item()
        expect(self._grid.cell(LINE, PRODUCT)).to_have_text(self._item, timeout=WINDOW_TIMEOUT_MS)
        self._edit_cell(QUANTITY, ONE)
        self.reprice(amount)

    def reprice(self, amount: Decimal) -> None:
        self._edit_cell(RATE, amount)
        pattern = re.compile(rf"^\s*{amount_pattern(amount)}\s*$")
        expect(self._grid.cell(LINE, AMOUNT)).to_have_text(pattern, timeout=WINDOW_TIMEOUT_MS)

    def _pick_item(self) -> None:
        self._grid.cell(LINE, PRODUCT).click()
        self._page.keyboard.press("Enter")
        search = self._picker.get_by_role("searchbox").first
        expect(search).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        search.press("Control+A")
        search.press_sequentially(self._item, delay=KEY_DELAY_MS)
        expect(self._highlighted_item).to_be_visible(timeout=SEARCH_RESULT_TIMEOUT_MS)
        self._press_enter_until_picked(search)

    def _press_enter_until_picked(self, search: Locator) -> None:
        """A cold app ignores the first Enter on the item list (as in GarmentsSalePage), so it is repeated."""
        for _ in range(PICK_ATTEMPTS):
            search.press("Enter")
            if disappears_within(self._picker, PICK_ATTEMPT_MS):
                return
        expect(self._picker).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    def _edit_cell(self, column: str, value: Decimal) -> None:
        """Uses the cell's editor when it is already open (picking the item opens Qty, value selected)."""
        cell = self._grid.cell(LINE, column)
        # Why an id: the editor is an ag-Grid popup rendered outside the cell; the app names it by column.
        editor = self._page.locator(f"#txt-{column}-{LINE}")
        if not appears_within(editor, EDITOR_LOOKUP_MS):
            cell.dblclick()
        expect(editor).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        editor.press("Control+A")
        editor.press_sequentially(format(value, "f"))
        editor.press("Enter")
        self._document.close_item_details()

    @property
    def _highlighted_item(self) -> Locator:
        # Why a class: ag-Grid marks the row Enter will pick only with ag-row-selected.
        return self._picker.locator(".ag-row-selected").filter(
            has=self._page.get_by_text(self._item, exact=True)
        )

    @property
    def _picker(self) -> Locator:
        return self._page.locator("ngb-modal-window").filter(has_text="Select Item")
