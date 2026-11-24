"""What sale bills and sale returns share in the outstanding cases: one 0% GST line priced at the document's
amount, re-pricing that line, closing what a save leaves open, and the list actions.
"""

import re
from decimal import Decimal

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, expect

from pages.accounting.bill_adjustment import BillAdjustmentWindow
from pages.accounting.outstanding.document_list import DocumentList
from pages.accounting.outstanding.item_line import OneItemLine
from pages.components.bill_totals import BillTotals
from pages.components.confirm_dialog import ConfirmDialog
from pages.dashboard_page import DashboardPage
from pages.sale.documents.document import SaleDocument
from pages.sale.documents.mode_of_payment import ModeOfPayment
from pages.sale.documents.screen import is_shown_within

RATE = "salePurchaseRate"
DELETE_ACTION = "Delete"
LINE_TIMEOUT_MS = 30_000
PRINT_LOOKUP_MS = 10_000
ADJUSTMENT_LOOKUP_MS = 8_000
PRINT_WINDOW_TEXT = "Select Format"
FIRST_EMPTY_ROW = 1
BARCODE_COLUMN = "tmp_barcode"
PAYMENT_WINDOW_LOOKUP_MS = 5_000

Allocations = dict[str, Decimal]


class UnexpectedNewDocumentsError(AssertionError):
    def __init__(self, party: str, numbers: list[str]) -> None:
        super().__init__(f"Expected one new document for {party} after saving, found {numbers}")


class DocumentDesk:
    def __init__(self, page: Page, item: str, document: SaleDocument) -> None:
        self._page = page
        self._document = document
        self._line = OneItemLine(document, item)
        self._list = DocumentList(page, document.menu)
        self._adjustment = BillAdjustmentWindow(page)
        self._known_numbers: set[str] = set()

    def delete(self, number: str) -> None:
        self._list.choose_from_menu(number, DELETE_ACTION)
        ConfirmDialog(self._page).answer_yes()
        self._document.screen.expect_toast("success")

    def _saved_number(self, party: str) -> str:
        """The number of the document just saved for the party, read from the list after saving. The
        number shown before saving can be taken by another user's save in between (OA-010, 2026-10-09:
        0000069 shown, 0000070 saved)."""
        new_numbers = set(self._list.numbers_for(party)) - self._known_numbers
        if len(new_numbers) != 1:
            raise UnexpectedNewDocumentsError(party, sorted(new_numbers))
        number = new_numbers.pop()
        self._known_numbers.add(number)
        return number

    def _start_for(self, party: str) -> None:
        """Opens a new document for the party. A ledger saved seconds earlier is sometimes missing from
        Select Party ("Not Found!", OA-010 on 2026-10-09); the unsaved document is left and opened again.
        A page reload is not used: the router restores a half-filled form after a reload."""
        try:
            self._open_new_for(party)
        except (AssertionError, PlaywrightError):
            if self._document_is_open():
                BillTotals(self._page).leave_without_saving()
            self._open_new_for(party)

    def _document_is_open(self) -> bool:
        # The document's Close (Esc) button has an id per window, e.g. btnEsc88.
        return self._page.locator("[id^=btnEsc]").first.is_visible()

    def _open_new_for(self, party: str) -> None:
        DashboardPage(self._page).open()
        self._document.open_new()
        self._choose_party(party)

    def _choose_party(self, party: str) -> None:
        self._document.choose_party(party)

    def _open_for_change(self, number: str) -> None:
        self._list.open_for_change(number)
        expect(self._rate_cell).to_be_visible(timeout=LINE_TIMEOUT_MS)

    def _reprice(self, amount: Decimal) -> None:
        self._line.reprice(amount)

    def _save_from_footer(self) -> None:
        """Tab on the first empty grid row, as a user leaves the grid, marks the document so the save opens
        Bill Adjustment (`isTabkeypressingrid`, processout.transaction.component.ts:7299); the footer's
        Save button then saves wherever focus landed. End alone stopped working on app V. 4.3.599.b when
        focus was in a header field (Mobile No., OA-016 on 2026-10-12)."""
        # The barcode cell, not the product cell: clicking an empty product cell opens Select Item on app
        # V. 4.3.599.b, and that window then covers the Save button.
        self._document.grid.cell(FIRST_EMPTY_ROW, BARCODE_COLUMN).click()
        self._page.keyboard.press("Tab")
        if self._document.selection.is_shown():
            self._page.keyboard.press("Escape")
        # Why an id prefix: the footer Save button's id carries the window number (btnSave88).
        self._page.locator("[id^=btnSave]").locator("visible=true").first.click()
        # On V. 4.3.599.b the first save only moves focus into the Additional Details (expenses) grid; a
        # second F10 opens Mode Of Payment (probe 2026-10-12).
        if not ModeOfPayment(self._page).is_open(PAYMENT_WINDOW_LOOKUP_MS):
            self._page.keyboard.press("F10")

    def _settle_adjustment(self, allocations: Allocations) -> None:
        """Allocates in the Bill Adjustment window when the save opens it; an empty allocation leaves the
        whole amount unadjusted (New Ref / advance)."""
        if not self._adjustment.is_open(ADJUSTMENT_LOOKUP_MS):
            return
        self._adjustment.allocate(allocations)
        self._adjustment.save()

    def _accept_adjustment_as_shown(self) -> None:
        """Saves the Bill Adjustment window as the app proposes it, when the save opens it."""
        if self._adjustment.is_open(ADJUSTMENT_LOOKUP_MS):
            self._adjustment.save()

    def _close_print_window(self) -> None:
        close = self._print_window.get_by_role("button", name=re.compile("Close"))
        if is_shown_within(close, PRINT_LOOKUP_MS):
            close.click()
        self._document.screen.wait_for_loader()
        self._document.leave_to_list()

    @property
    def _rate_cell(self) -> Locator:
        return self._document.grid.cell(0, RATE)

    @property
    def _print_window(self) -> Locator:
        return self._page.locator("ngb-modal-window").filter(has_text=PRINT_WINDOW_TEXT)
