"""Purchase > Order: enter, save, close, convert to a bill."""

from decimal import Decimal

from pages.purchase.documents import messages
from pages.purchase.documents.dates import timestamp_label, todays_serial
from pages.purchase.documents.document_list import RowAction
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.feedback import ToastKind
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.selection_window import PendingKind

CONVERSION_BILL_DISCOUNT = Decimal(10)  # the original always converts with a 10 bill discount
CLOSED_STATUS = "Closed"
SAVED_TOAST_TIMEOUT_MS = 50_000
CONVERSION_PROMPT_TIMEOUT_MS = 1_500


class PurchaseOrderPage(PurchaseEntryForm):
    screen = PurchaseScreen.ORDER
    number_label = "Order No."
    saved_message = messages.ORDER_SAVED

    def close_order(self, number: str) -> None:
        """Closes the order, checks it reads Closed, then tries to delete it (warning expected)."""
        self.menu.open_purchase(self.screen)
        self.documents.find(number)
        self.documents.choose_action(number, RowAction.CLOSE)
        self.feedback.confirm_if_asked()
        self.documents.find(number)
        self.documents.expect_row_status(number, CLOSED_STATUS)
        self.documents.choose_action(number, RowAction.DELETE)
        self.feedback.expect_toast(ToastKind.WARNING)

    def convert_to_bill(self, number: str) -> None:
        """Turns the order into a purchase bill (10 bill discount, dated today), then removes the order."""
        self.menu.open_purchase(self.screen)
        self.documents.find(number)
        self.documents.choose_action(number, RowAction.CONVERT)
        self.feedback.confirm_if_asked()
        self._start_manual_entry()
        self._complete_bill_header()
        self.footer.enter_bill_discount(CONVERSION_BILL_DISCOUNT)
        self.save()
        self._confirm_conversion_saved()
        self.menu.open_purchase(self.screen)
        self.documents.delete_after_conversion(number)

    def _after_vendor(self, draft: PurchaseDraft) -> None:
        self.feedback.wait_for_loader()
        self._number_field.fill(timestamp_label())
        self._number_field.press("Enter")
        self._accept_typed_number()
        self._offer_pending(PendingKind.QUOTATION, draft.quotation_number)

    def fill_lines(self, draft: PurchaseDraft) -> None:
        if draft.quotation_number:
            self.grid.expect_line_carried(0, draft.lines[0])
        else:
            super().fill_lines(draft)

    def _complete_bill_header(self) -> None:
        self._invoice_number_field.fill(timestamp_label())
        self.grid.expect_product_not_editing(0)
        self._enter_date("Entry Date", todays_serial())
        self._enter_date("Invoice Date", todays_serial())

    def _confirm_conversion_saved(self) -> None:
        self.feedback.wait_for_loader()
        self._press_save_in_prompt(CONVERSION_PROMPT_TIMEOUT_MS)
        self.feedback.expect_toast(ToastKind.SUCCESS, SAVED_TOAST_TIMEOUT_MS)
        self.feedback.wait_for_loader()
        self.return_to_list()
