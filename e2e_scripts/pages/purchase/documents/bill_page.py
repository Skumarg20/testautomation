"""Purchase > Bill (item master items, batches, optional source documents).

The older `purchase_bill_page.PurchaseBillPage` is the garments Alt+P window, a different screen.
"""

from playwright.sync_api import expect

from pages.purchase.documents import messages
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.document_list import RowAction
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.feedback import ToastKind
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.selection_window import PendingKind
from pages.purchase.documents.stock_entry import enter_batch_and_expiry, enter_sale_prices

SAVED_TOAST_TIMEOUT_MS = 50_000
CHALLAN_PROMPT_TIMEOUT_MS = 5_000
SAVE_PROMPT_TIMEOUT_MS = 2_000


class PurchaseBillEntryPage(PurchaseEntryForm):
    screen = PurchaseScreen.BILL
    number_label = "Invoice No."
    saved_message = messages.BILL_SAVED

    def complete_header(self, draft: PurchaseDraft) -> None:
        self._invoice_number_field.fill(timestamp_label())
        if draft.invoice_date is not None:
            self._enter_date("Invoice Date", draft.invoice_date)
        self._offer_pending(PendingKind.CHALLAN, draft.challan_number)
        self._offer_pending(PendingKind.ORDER, draft.order_number)
        self._offer_pending(PendingKind.QUOTATION, "")

    def fill_lines(self, draft: PurchaseDraft) -> None:
        if draft.challan_number:
            self.grid.expect_line_carried(0, draft.lines[0])
        elif draft.order_number:
            self.grid.expect_line_carried(0, draft.lines[0])
            enter_batch_and_expiry(self.grid, draft.lines)
        else:
            super().fill_lines(draft)

    def delete_with_challan(self, number: str) -> None:
        """Deletes a bill that was made from a challan, and the challan with it."""
        self._open_delete_choice(number)
        self.page.get_by_role("button", name="Delete Bill & Challan").click()
        self.feedback.confirm_if_asked()
        self.feedback.expect_toast(ToastKind.SUCCESS, SAVED_TOAST_TIMEOUT_MS)
        self.feedback.wait_for_loader()

    def reconvert_to_challan(self, number: str, challan_number: str) -> None:
        """Deletes the bill but keeps its challan open again, then checks the challan is listed."""
        self._open_delete_choice(number)
        self.page.get_by_role("button", name="Re-Convert into Challan").click()
        self.feedback.confirm_if_asked()
        self.feedback.expect_toast(ToastKind.SUCCESS, SAVED_TOAST_TIMEOUT_MS)
        self.feedback.wait_for_loader()
        self.menu.open_purchase(PurchaseScreen.CHALLAN)
        self.documents.filter_this_week()
        self.documents.find(challan_number)
        self.documents.expect_row_visible(challan_number)

    def _open_delete_choice(self, number: str) -> None:
        self.menu.open_purchase(self.screen)
        self.documents.find(number)
        self.documents.choose_action(number, RowAction.DELETE)
        self.feedback.wait_for_loader()
        # The window asks whether to delete the challan too; it is a custom element without a role.
        window = self.page.locator("div.modal-content delete-load-challan-window")
        expect(window).to_be_visible(timeout=CHALLAN_PROMPT_TIMEOUT_MS)

    def _after_vendor(self, draft: PurchaseDraft) -> None:
        self.feedback.wait_for_loader()
        self._start_manual_entry()

    def _enter_batch_details(self, row: int, line: PurchaseLineItem) -> None:
        self.grid.type_batch(row, line.batch)
        self.grid.enter_expiry(row, line.expiry_serial)

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        super()._enter_price_details(row, line)
        enter_sale_prices(self.page, line)

    def _confirm_save_prompt(self) -> None:
        self.feedback.wait_for_loader()
        self._press_save_in_prompt(SAVE_PROMPT_TIMEOUT_MS)
