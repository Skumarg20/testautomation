"""What every purchase document screen (order, challan, bill, return) has in common."""

import re
from decimal import Decimal
from enum import Enum

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.documents import messages
from pages.purchase.documents.dates import entry_date_text
from pages.purchase.documents.document_list import DocumentList
from pages.purchase.documents.drafts import PurchaseDraft, Refusal
from pages.purchase.documents.entry_grid import EntryGrid
from pages.purchase.documents.feedback import AppFeedback, ToastKind, appears_within
from pages.purchase.documents.fields import labelled_input
from pages.purchase.documents.invoice_footer import InvoiceFooter
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.purchase.documents.navigation import ModuleMenu, PurchaseScreen
from pages.purchase.documents.selection_window import PendingDocumentWindow, PendingKind, SelectionWindow

PENDING_WINDOW_TIMEOUT_MS = 3_000
PRINT_WINDOW_TIMEOUT_MS = 3_000
SAVE_PROMPT_TIMEOUT_MS = 2_000
PREFERENCES_TIMEOUT_MS = 2_000
UNSAVED_TIMEOUT_MS = 1_000
SAVED_TOAST_TIMEOUT_MS = 50_000
VENDOR_CLOSED_TIMEOUT_MS = 10_000
WARNING_RETRY_TIMEOUT_MS = 500
NUMBER_PROMPT_TIMEOUT_MS = 1_500
SAVE_STEP_TIMEOUT_MS = 4_000
SETTLED_TIMEOUT_MS = 300
MAX_SAVE_PRESSES = 4
MAX_OPEN_DIALOGS = 3
SAVE_BUTTON = re.compile(r"^save$", re.IGNORECASE)


class LineOutcome(Enum):
    ENTERED = "entered"
    NO_PRODUCT = "no product chosen"
    QUANTITY_REFUSED = "quantity refused"


class LinesNotEnteredError(AssertionError):
    def __init__(self, outcome: LineOutcome) -> None:
        super().__init__(f"The product lines were not entered: {outcome.value}")


# Why a pattern: the label breaks over two lines ("F10 / End", "Save"), so the text may have no space.
END_SAVE = re.compile(r"End\s*Save")


class PurchaseEntryForm(BasePage):
    screen: PurchaseScreen
    number_label: str
    saved_message: str

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.menu = ModuleMenu(page)
        self.documents = DocumentList(page)
        self.feedback = AppFeedback(page)
        self.grid = EntryGrid(page)
        self.footer = InvoiceFooter(page)
        self.vendor_window = SelectionWindow(page)
        self.pending = PendingDocumentWindow(page)

    def create(self, draft: PurchaseDraft) -> str:
        """The whole happy path: fill, save, wait for the app to confirm. Returns the document number."""
        self.begin(draft)
        self.enter_entry_date(draft.entry_date)
        self.complete_header(draft)
        self.fill_lines(draft)
        number = self.finish(draft)
        self.expect_saved()
        return number

    def expect_refused(self, draft: PurchaseDraft) -> None:
        """Fills the document as a NEGATIVE sheet row says and checks the app refuses with its own message."""
        refusal = draft.expected_refusal()
        self.begin(draft)
        if refusal is Refusal.NO_PARTY:
            self.expect_vendor_empty()
            self.expect_save_refused_for_no_item()
        elif refusal is Refusal.BACK_DATE:
            self.enter_entry_date(draft.entry_date)
            self.expect_entry_date_refused(messages.BACK_DATE)
        else:
            self._expect_line_refused(draft, refusal)
        self.return_to_list()

    def expect_save_refused_for_no_item(self) -> None:
        """Save on a document with no product is refused; the app checks this before anything else."""
        self.press_save()
        self.feedback.expect_toast_saying(ToastKind.WARNING, messages.NO_ITEM)

    def _expect_line_refused(self, draft: PurchaseDraft, refusal: Refusal) -> None:
        self.enter_entry_date(draft.entry_date)
        self.complete_header(draft)
        outcome = self.add_lines(draft.lines)
        if refusal is Refusal.NO_PRODUCT:
            self.expect_save_refused_for_no_item()
        else:
            assert outcome is LineOutcome.QUANTITY_REFUSED

    def begin(self, draft: PurchaseDraft) -> None:
        self.open_new()
        self.choose_vendor(draft.party)
        if draft.party:
            self._after_vendor(draft)

    def open_new(self) -> None:
        self.menu.open_purchase(self.screen)
        self.documents.create()
        self._discard_leftover_windows()

    def choose_vendor(self, name: str) -> None:
        if not self._party_window_opened_by_itself():
            self._party_field.click()
        if name:
            self.vendor_window.choose_cell_text(name)
        else:
            self.feedback.wait_for_loader()
            self.vendor_window.close_with_cross()
        expect(self.page.locator("div.modal-dialog.modal-lg")).to_be_hidden(timeout=VENDOR_CLOSED_TIMEOUT_MS)

    def _party_window_opened_by_itself(self) -> bool:
        """Seen live 2026-10-08: Create/F2 opens "Select Party" at once, covering the Party Name field."""
        if appears_within(self.page.locator("div.frameModal"), PREFERENCES_TIMEOUT_MS):
            return True
        self.feedback.wait_for_loader()
        return self.vendor_window.is_open()

    def expect_vendor_empty(self) -> None:
        expect(self._party_field).to_have_value("")

    def enter_entry_date(self, serial: int) -> None:
        self._enter_date("Entry Date", serial)

    def expect_entry_date_refused(self, message: str) -> None:
        """A date the app does not allow is answered with a warning when the date is entered or left."""
        if not self.feedback.toast_appears_saying(ToastKind.WARNING, message, WARNING_RETRY_TIMEOUT_MS):
            self.grid.click_product_cell(0)
        self.feedback.expect_toast_saying(ToastKind.WARNING, message)

    def complete_header(self, draft: PurchaseDraft) -> None:
        """Header fields that come after the date; most screens have none."""

    def enter_invoice_date(self, serial: int) -> None:
        self._enter_date("Invoice Date", serial)

    def enter_number(self, text: str) -> None:
        """Typed key by key, so the field's own length limit applies; Enter makes the app check it."""
        field = self._number_field
        field.press_sequentially(text)
        field.press("Enter")
        self._accept_typed_number()

    def expect_number(self, text: str) -> None:
        expect(self._number_field).to_have_value(text)

    def expect_dates(self, entry_date: int, invoice_date: int) -> None:
        expect(labelled_input(self.page, "Entry Date")).to_have_value(entry_date_text(entry_date))
        expect(labelled_input(self.page, "Invoice Date")).to_have_value(entry_date_text(invoice_date))

    def discard(self) -> None:
        """Closes the open document without saving; the app asks first when something was entered."""
        self._dismiss_open_alerts()
        # Why an id prefix: the Close button's id ends in the tab number; the newest tab is last.
        self.page.locator("[id^=btnEsc]").last.click()
        self.feedback.confirm_if_asked()

    def fill_lines(self, draft: PurchaseDraft) -> None:
        outcome = self.add_lines(draft.lines)
        if outcome is not LineOutcome.ENTERED:
            raise LinesNotEnteredError(outcome)

    def add_lines(self, lines: tuple[PurchaseLineItem, ...]) -> LineOutcome:
        for row, line in enumerate(lines):
            outcome = self._add_line(row, line)
            if outcome is not LineOutcome.ENTERED:
                return outcome
        return LineOutcome.ENTERED

    def finish(self, draft: PurchaseDraft) -> str:
        """Bill discount, a check of the calculated total, then save. Returns the document number."""
        self.footer.enter_bill_discount(draft.bill_discount)
        self.footer.expect_invoice_value_consistent()
        return self.save()

    def save(self) -> str:
        number = self.current_number()
        self.press_save()
        return number

    def _dismiss_open_alerts(self) -> None:
        """A dialog still open over the bill (an alert, a picker) swallows the click on Close."""
        dialogs = self.page.locator("ngb-modal-window:not([aria-hidden='true'])")
        for _ in range(MAX_OPEN_DIALOGS):
            if not appears_within(dialogs, SETTLED_TIMEOUT_MS):
                return
            self.page.keyboard.press("Escape")

    def current_number(self) -> str:
        return self._number_field.input_value()

    def type_bill_value(self, amount: Decimal) -> None:
        """Overwrites the bill value the app calculated; the bill is posted with the typed value."""
        field = self.footer.bill_value_field
        field.click()
        field.press("Control+A")
        field.press_sequentially(str(amount))

    def press_save(self) -> None:
        # Why the button: End only moves focus onto Save on this screen and sends nothing (seen 2026-10-14).
        # Why an id prefix: the button's id ends in the tab number (btnSave61); the newest tab is last.
        self.page.locator("[id^=btnSave]").filter(has_text=END_SAVE).last.click()

    def expect_saved(self) -> None:
        self._step_through_save()
        self._confirm_save_prompt()
        self.feedback.expect_toast_saying(ToastKind.SUCCESS, self.saved_message, SAVED_TOAST_TIMEOUT_MS)
        self.feedback.wait_for_loader()
        self.return_to_list()

    def _step_through_save(self) -> None:
        """Save does not save at once: it walks the bill discount, then the bill value; the press made
        while the bill value holds focus saves. Each stage is waited for, so a save is never pressed twice."""
        for _ in range(MAX_SAVE_PRESSES):
            if self._save_is_under_way():
                return
            if self._bill_value_has_focus():
                self.press_save()
                return
            self.press_save()

    def _save_is_under_way(self) -> bool:
        """True once the app answers the last press with a toast or a payment window; false at a next step."""
        discount = self.footer.bill_discount_field.and_(self.page.locator(":focus"))
        bill_value = self.footer.bill_value_field.and_(self.page.locator(":focus"))
        answered = self.feedback.any_toast().or_(self.page.locator("div.frameModal"))
        return appears_within(
            answered.or_(discount).or_(bill_value), SAVE_STEP_TIMEOUT_MS
        ) and appears_within(answered, SETTLED_TIMEOUT_MS)

    def _bill_value_has_focus(self) -> bool:
        return appears_within(
            self.footer.bill_value_field.and_(self.page.locator(":focus")), SETTLED_TIMEOUT_MS
        )

    def delete(self, number: str) -> None:
        self.menu.open_purchase(self.screen)
        self.documents.delete(number)

    def return_to_list(self) -> None:
        if appears_within(self.page.locator("#billDetailForm"), PRINT_WINDOW_TIMEOUT_MS):
            self.page.locator("div.modal-header.p-2").get_by_text("×").click()
        self.feedback.confirm_if_asked()
        if self.vendor_window.is_open():
            self.vendor_window.close_without_choosing()
        self._close_pending_windows()
        self.feedback.confirm_if_asked()

    def _after_vendor(self, draft: PurchaseDraft) -> None:
        """Steps that follow choosing the party; they differ per screen."""

    def _enter_batch_details(self, row: int, line: PurchaseLineItem) -> None:
        """Batch, expiry and the like, entered before the quantity; only some screens have them."""

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        self.grid.enter_free(row, line.free)
        self.grid.enter_rate(row, line.rate)
        self.grid.enter_discounts(row, line)

    def _add_line(self, row: int, line: PurchaseLineItem) -> LineOutcome:
        self.grid.select_product(row, line.product)
        if not line.product:
            self.grid.expect_product_empty(row)
            return LineOutcome.NO_PRODUCT
        self._enter_batch_details(row, line)
        self.grid.enter_quantity(row, line.quantity)
        if line.quantity < Decimal(1):
            return LineOutcome.QUANTITY_REFUSED
        self._enter_price_details(row, line)
        return LineOutcome.ENTERED

    def _enter_date(self, label: str, serial: int) -> None:
        field = labelled_input(self.page, label)
        field.press("Control+A")
        field.press_sequentially(entry_date_text(serial))
        field.press("Enter")

    def _offer_pending(self, kind: PendingKind, number: str) -> None:
        """Takes the named document over if the app lists it; otherwise closes the list if it opened."""
        if not self.pending.is_open(kind, PENDING_WINDOW_TIMEOUT_MS):
            return
        if number:
            self.pending.pull_in(kind, number)
        else:
            self.pending.close(kind)

    def _close_pending_windows(self) -> None:
        for kind in PendingKind:
            if self.pending.is_open(kind, WARNING_RETRY_TIMEOUT_MS):
                self.pending.close(kind)

    def _start_manual_entry(self) -> None:
        popup = self.page.locator("div.popup-container.ng-star-inserted")
        if not appears_within(popup, PENDING_WINDOW_TIMEOUT_MS):
            return
        manual = self.page.get_by_role("button", name="Start Manual Entry")
        if appears_within(manual, SAVE_PROMPT_TIMEOUT_MS):
            manual.click()
        else:
            self.page.locator("div.manual-entry").click()

    def _accept_typed_number(self) -> None:
        """With auto-numbering on, a number typed over the generated one asks "Change <label>?"."""
        prompt = self.page.locator("ngb-modal-window").filter(has_text="Are you sure want to change")
        if appears_within(prompt, NUMBER_PROMPT_TIMEOUT_MS):
            prompt.get_by_role("button", name="Yes").click()
            expect(prompt).to_be_hidden()

    def _discard_leftover_windows(self) -> None:
        """A document left open earlier can pop its "unsaved" window or the preferences window again."""
        self._close_unsaved_window()
        if appears_within(self.page.locator("div.frameModal"), PREFERENCES_TIMEOUT_MS):
            self.feedback.close_stacked_modals()
            self.page.get_by_role("button", name=SAVE_BUTTON).click()
            self.feedback.wait_for_loader()
        self._close_unsaved_window()

    def _close_unsaved_window(self) -> None:
        unsaved = self.page.locator("ngb-modal-window:not([aria-hidden='true']) unsave-bill div.modal-header")
        if appears_within(unsaved, UNSAVED_TIMEOUT_MS) and self.vendor_window.cross_is_shown(
            UNSAVED_TIMEOUT_MS
        ):
            self.vendor_window.close_with_cross()

    def _confirm_save_prompt(self) -> None:
        """Some saves ask for one more Save in a window; the original handles it only on bill and return."""

    def _press_save_in_prompt(self, timeout_ms: int) -> None:
        self.feedback.close_stacked_modals()
        if appears_within(self.page.locator("div.frameModal"), timeout_ms):
            self.page.get_by_role("button", name=SAVE_BUTTON).click()

    @property
    def _party_field(self) -> Locator:
        return labelled_input(self.page, "Party Name")

    @property
    def _number_field(self) -> Locator:
        return labelled_input(self.page, self.number_label)

    @property
    def _invoice_number_field(self) -> Locator:
        return labelled_input(self.page, "Invoice No.")
