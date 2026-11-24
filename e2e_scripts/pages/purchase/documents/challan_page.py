"""Purchase > Challan: enter (directly or from an order), save. A challan receives stock like a bill."""

from pages.purchase.documents import messages
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.selection_window import PendingKind
from pages.purchase.documents.stock_entry import enter_batch_and_expiry, enter_sale_prices


class PurchaseChallanPage(PurchaseEntryForm):
    screen = PurchaseScreen.CHALLAN
    number_label = "Challan No."
    saved_message = messages.CHALLAN_SAVED

    def complete_header(self, draft: PurchaseDraft) -> None:
        self._number_field.fill(timestamp_label())
        self._number_field.press("Enter")
        self._accept_typed_number()
        self.feedback.wait_for_loader()
        self._offer_pending(PendingKind.ORDER, draft.order_number)
        self._offer_pending(PendingKind.QUOTATION, "")

    def fill_lines(self, draft: PurchaseDraft) -> None:
        if draft.order_number:
            self.grid.expect_line_carried(0, draft.lines[0])
            enter_batch_and_expiry(self.grid, draft.lines)
        else:
            super().fill_lines(draft)

    def _after_vendor(self, draft: PurchaseDraft) -> None:
        self.feedback.wait_for_loader()
        self._offer_pending(PendingKind.ORDER, draft.order_number)
        self._offer_pending(PendingKind.QUOTATION, "")

    def _enter_batch_details(self, row: int, line: PurchaseLineItem) -> None:
        self.grid.type_batch(row, line.batch)
        self.grid.enter_expiry(row, line.expiry_serial)

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        super()._enter_price_details(row, line)
        enter_sale_prices(self.page, line)
