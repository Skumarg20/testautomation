"""The Bill Adjustment window: allocates a receipt or sale return to a party's bills; the rest is advance.

Keys (bill.adjustment.new.component.ts:1766-1795): Space selects a row and fills it with the smaller of
the bill balance and the pending amount, then opens the Adjusted Amt. editor; F10 saves; Esc closes.
Saving with an amount still pending asks "<n> Amount will be transfered into Advance. Want to proceed ?"
(:1687; button Proceed); the window then switches Reference Type to Advance (value 2) and F10 saves again.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.confirmation import Confirmation
from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within, disappears_within
from pages.base_page import BasePage
from pages.components.bill_totals import amount_pattern

TITLE = "Bill Adjustment"
INVOICE_NUMBER = "cus_invoiceNo"
ADJUSTED_AMOUNT = "adjustmentAmount"
OVER_BILL_VALUE = re.compile(r"cannot exceed the bill value", re.IGNORECASE)
WINDOW_TIMEOUT_MS = 20_000
EDITOR_TIMEOUT_MS = 10_000
EDITOR_LOOKUP_MS = 5_000
ADVANCE_QUESTION_LOOKUP_MS = 3_000
CLOSE_TIMEOUT_MS = 15_000
TOGGLE_TIMEOUT_MS = 10_000
AUTO_CLOSE_LOOKUP_MS = 2_000
MAX_ROWS = 20
SELECTED_ROW = re.compile(r"\bag-row-selected\b")
FOCUSED_ROW = re.compile(r"\bag-row-focus\b")
ADVANCE_REFERENCE = "2"
AGAINST_REFERENCE = "1"
REFERENCE_SWITCH_ATTEMPTS = 3
REFERENCE_SETTLE_MS = 3_000
SELECTION_SETTLE_MS = 3_000


class BillAdjustmentWindow(BasePage):
    def expect_open(self) -> None:
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def is_open(self, timeout_ms: int) -> bool:
        return appears_within(self._window, timeout_ms)

    def adjust(self, invoice_number: str, amount: Decimal) -> None:
        """Selects the bill, then types the amount to adjust to it."""
        if not self._is_selected(invoice_number):
            self._toggle(invoice_number)
        self._type_adjusted_amount(invoice_number, amount)

    def allocate(self, allocations: dict[str, Decimal]) -> None:
        """Leaves exactly these bill adjustments. With nothing to allocate an Advance view is kept as it is:
        a party with no bills opens in it and has no bill list to switch to (OA-062, 2026-10-13).
        Reopened from a sale document the window is read-only until its Modify (F3) button is pressed
        (bill.adjustment.new.component.ts:1658, OA-028)."""
        self._unlock_if_read_only()
        if allocations:
            self._release_advance()
            self.show_bills()
        if self._shows_bills():
            self.unselect_all()
        for bill_number, amount in allocations.items():
            self.adjust(bill_number, amount)

    def show_bills(self) -> None:
        """A credit saved as an advance reopens in the Advance view (Ref No AD.., no bills; OA-062,
        2026-10-12); Agst Ref lists the party's bills again. The app moves such a credit to the Advance view
        a moment after the window opens (bill.adjustment.new.component.ts:388), which undid a switch made
        before it (OA-062, 2026-10-14), so the switch is repeated until it holds."""
        for _ in range(REFERENCE_SWITCH_ATTEMPTS):
            if self._shows_bills() and not self._turns_to_advance_within(REFERENCE_SETTLE_MS):
                return
            self._reference_type.select_option(AGAINST_REFERENCE)
            # The first column reads "Invoice No." or "Ref No" by document, so the value is checked.
            expect(self._reference_type).to_have_value(AGAINST_REFERENCE, timeout=CLOSE_TIMEOUT_MS)
        attempts = REFERENCE_SWITCH_ATTEMPTS
        raise AssertionError(f"Bill Adjustment went back to the Advance view after {attempts} switches")

    def unselect_all(self) -> None:
        """Unticks the selected bill rows one at a time. The window hides fully settled bills and shows
        them again as they change (bill.adjustment.new.component.ts:272), so a list of numbers taken up
        front goes stale (OA-072, 2026-10-13); each pass reads the current selection instead. The window
        ticks the adjusted bills a moment after it opens (bill.adjustment.new.component.ts:380), so a check
        made at once found nothing to untick and the un-adjust was saved unchanged (OA-091, 2026-10-14)."""
        selected = self._rows.and_(self.page.locator(".ag-row-selected"))
        if not appears_within(selected, SELECTION_SETTLE_MS):
            return
        for _ in range(MAX_ROWS):
            if selected.count() == 0:
                return
            invoice_number = selected.first.locator(f'[col-id="{INVOICE_NUMBER}"]').inner_text().strip()
            self._toggle(invoice_number)
        raise AssertionError(f"Bill Adjustment still had selected rows after {MAX_ROWS} untick attempts")

    def expect_over_bill_value_refused(self, invoice_number: str, amount: Decimal) -> None:
        """Adjusting more than the bill's balance is refused ("The entered amount cannot exceed the bill
        value", bill.adjustment.new.component.ts:1424)."""
        self.adjust(invoice_number, amount)
        Toasts(self.page).expect_any_saying(OVER_BILL_VALUE)

    def save(self) -> None:
        """Clicks Save (Update when changing); a pending remainder is accepted as advance (Proceed, then Save
        again in the advance view). The button is clicked rather than F10 pressed: with focus outside the
        grid F10 did nothing (OA-019, 2026-10-12). When the allocation leaves nothing pending, the app may
        save and close the window by itself (OA-019, 2026-10-13); then there is nothing to click."""
        if disappears_within(self._window, AUTO_CLOSE_LOOKUP_MS):
            return
        self._click_save()
        confirmation = Confirmation(self.page)
        if confirmation.is_asked(ADVANCE_QUESTION_LOOKUP_MS):
            confirmation.answer_yes()
            expect(self._reference_type).to_have_value(ADVANCE_REFERENCE, timeout=CLOSE_TIMEOUT_MS)
            self._confirm_advance_amount()
        if not disappears_within(self._window, CLOSE_TIMEOUT_MS):
            self._click_save()
        expect(self._window).to_be_hidden(timeout=CLOSE_TIMEOUT_MS)

    def _confirm_advance_amount(self) -> None:
        """After Proceed the app opens the advance row's amount editor; Update clicked over it left the window
        open (OA-069, 2026-10-14). Enter in the editor saves when nothing is pending
        (bill.adjustment.new.component.ts, actionOnEnter), so it is pressed first and Save is the fallback."""
        editor = self.page.locator(f'[id^="txt-{ADJUSTED_AMOUNT}-"]').first
        if appears_within(editor, EDITOR_LOOKUP_MS):
            editor.press("Enter")
        if not disappears_within(self._window, AUTO_CLOSE_LOOKUP_MS):
            self._click_save()

    def _unlock_if_read_only(self) -> None:
        modify = self._window.locator("#btn-Modify")
        if modify.is_visible():
            modify.click()

    def _release_advance(self) -> None:
        """An advance stays allocated in the Advance view even after the bills are adjusted (Adjusted
        1,600 for a 1,000 receipt; OA-062, 2026-10-14), and unticking its row does not release it: its
        Adjusted Amt. is what the app keeps (bill.adjustment.new.component.ts:1461). It is set to 0 and the
        editor left open: the app recounts the advance only when the Reference Type changes during an edit
        (:1037-1046); Enter would end the edit first. Saving then turns what is still pending into an
        advance again (:988)."""
        if self._shows_bills() and not self._turns_to_advance_within(REFERENCE_SETTLE_MS):
            return
        numbers = self._rows.locator(f'[col-id="{INVOICE_NUMBER}"]').all_inner_texts()
        for advance_number in filter(None, (number.strip() for number in numbers)):
            self._start_amount_edit(advance_number).fill("0")

    def _shows_bills(self) -> bool:
        return self._reference_type.input_value() == AGAINST_REFERENCE

    def _turns_to_advance_within(self, timeout_ms: int) -> bool:
        try:
            expect(self._reference_type).to_have_value(ADVANCE_REFERENCE, timeout=timeout_ms)
        except AssertionError:
            return False
        return True

    def _click_save(self) -> None:
        # Why ids: the buttons are named only by their title ("Save" / "Update"), which other windows reuse.
        self._window.locator("#btn-Save, #btn-Update").first.click()

    def close(self) -> None:
        self.page.keyboard.press("Escape")
        expect(self._window).to_be_hidden(timeout=CLOSE_TIMEOUT_MS)

    def _toggle(self, invoice_number: str) -> None:
        """Click the bill, then Space; waits until the row's selection has flipped (live 2026-10-09)."""
        was_selected = self._is_selected(invoice_number)
        row = self._row(invoice_number)
        self._focus(invoice_number)
        self.page.keyboard.press("Space")
        if was_selected:
            expect(row).not_to_have_class(SELECTED_ROW, timeout=TOGGLE_TIMEOUT_MS)
        else:
            expect(row).to_have_class(SELECTED_ROW, timeout=TOGGLE_TIMEOUT_MS)

    def _focus(self, invoice_number: str) -> None:
        """Click the bill and wait until any open amount editor has closed; a Space typed while the editor
        still has focus goes into the editor instead of toggling the row."""
        self._cell(invoice_number, INVOICE_NUMBER).click()
        expect(self._row(invoice_number)).to_have_class(FOCUSED_ROW, timeout=TOGGLE_TIMEOUT_MS)
        editor = self.page.locator(f'[id^="txt-{ADJUSTED_AMOUNT}-"]').first
        expect(editor).to_be_hidden(timeout=TOGGLE_TIMEOUT_MS)

    def _type_adjusted_amount(self, invoice_number: str, amount: Decimal) -> None:
        """Selecting a bill from a receipt opens its Adjusted Amt. editor a moment later (clicking the cell
        instead would untick the row). From a sale document no editor opens: the bill is filled with the
        smaller of the pending amount and its balance (bill.adjustment.new.component.ts:1186-1197), so that
        filled amount must already be the one wanted (OA-017, 2026-10-12)."""
        editor = self._editor(invoice_number)
        if not appears_within(editor, EDITOR_LOOKUP_MS):
            filled = re.compile(rf"^\s*{amount_pattern(amount)}")
            expect(self._cell(invoice_number, ADJUSTED_AMOUNT)).to_have_text(
                filled, timeout=EDITOR_TIMEOUT_MS
            )
            return
        self._type_into(editor, amount)

    def _start_amount_edit(self, invoice_number: str) -> Locator:
        """Opens the Adjusted Amt. editor of a row that is not being selected (an advance row)."""
        editor = self._editor(invoice_number)
        self._cell(invoice_number, ADJUSTED_AMOUNT).click()
        if not appears_within(editor, EDITOR_LOOKUP_MS):
            self.page.keyboard.press("Enter")
        expect(editor).to_be_visible(timeout=EDITOR_TIMEOUT_MS)
        return editor

    def _editor(self, invoice_number: str) -> Locator:
        row_index = self._row(invoice_number).get_attribute("row-index")
        # Why an id: the editor is an ag-Grid popup outside the cell; the app names it by column and row.
        return self.page.locator(f"#txt-{ADJUSTED_AMOUNT}-{row_index}")

    @staticmethod
    def _type_into(editor: Locator, amount: Decimal) -> None:
        # Why clear first: in an advance row's editor Control+A did not select, so "0" became 10000 (OA-062).
        editor.fill("")
        editor.press_sequentially(format(amount, "f"))
        editor.press("Enter")

    def _is_selected(self, invoice_number: str) -> bool:
        # Why a class: ag-Grid marks a ticked row with ag-row-selected (the row has hidden checkbox copies).
        return SELECTED_ROW.search(self._row(invoice_number).get_attribute("class") or "") is not None

    def _cell(self, invoice_number: str, column: str) -> Locator:
        return self._row(invoice_number).locator(f'[col-id="{column}"]').first

    def _row(self, invoice_number: str) -> Locator:
        invoice = self.page.locator(f'[col-id="{INVOICE_NUMBER}"]').get_by_text(invoice_number, exact=True)
        return self._rows.filter(has=invoice).first

    @property
    def _rows(self) -> Locator:
        # Why an id: the grid is ag-Grid without roles on its rows; the app gives the grid this id.
        return self._window.locator('#billAdjustmentGrid [ref="eBodyContainer"] .ag-row')

    @property
    def _reference_type(self) -> Locator:
        return self._window.locator("#drpRefType")

    @property
    def _window(self) -> Locator:
        return self.page.locator("ngb-modal-window").filter(has_text=TITLE)
