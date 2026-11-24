"""Purchase > Return: return goods to a vendor, either all items of one bill or items picked by hand."""

import re

from playwright.sync_api import Locator, expect

from pages.purchase.documents import messages
from pages.purchase.documents.drafts import PurchaseDraft, ReturnMode
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.entry_grid import GridProduct
from pages.purchase.documents.feedback import appears_within
from pages.purchase.documents.fields import labelled_input
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.selection_window import select_all_items

BILL_DETAILS_TIMEOUT_MS = 10_000
SAVE_PROMPT_TIMEOUT_MS = 2_000
OK_BUTTON = re.compile(r"^ok$", re.IGNORECASE)


class PurchaseReturnPage(PurchaseEntryForm):
    screen = PurchaseScreen.RETURN
    number_label = "Dr. Note"
    saved_message = messages.RETURN_SAVED

    def fill_lines(self, draft: PurchaseDraft) -> None:
        if draft.return_mode is ReturnMode.SINGLE:
            self.grid.expect_product_shown(0)
        else:
            super().fill_lines(draft)

    def look_up_bill_number(self, party: str, bill_number: str) -> None:
        """Opens a single-bill return and asks the app for a bill number, stopping before OK."""
        self.open_new()
        self.choose_vendor(party)
        self.feedback.wait_for_loader()
        expect(self._bill_details_window).to_be_visible(timeout=BILL_DETAILS_TIMEOUT_MS)
        self.page.locator("#returnOfBill").select_option(ReturnMode.SINGLE.value)
        number = labelled_input(self.page, "Bill No.")
        number.fill(bill_number)
        number.press("Enter")

    def returned_product(self) -> GridProduct:
        """The first product row as the app filled it from the bill (name, quantity, free quantity)."""
        return self.grid.product(0)

    def _after_vendor(self, draft: PurchaseDraft) -> None:
        """A single-bill return needs the bill-details window; without it the return would quietly become
        the default kind, so a late window fails. A manual return only answers the window if it opens."""
        self.feedback.wait_for_loader()
        if draft.return_mode is ReturnMode.SINGLE:
            expect(self._bill_details_window).to_be_visible(timeout=BILL_DETAILS_TIMEOUT_MS)
        elif not appears_within(self._bill_details_window, BILL_DETAILS_TIMEOUT_MS):
            return
        self.page.locator("#returnOfBill").select_option(draft.return_mode.value)
        if draft.return_mode is ReturnMode.SINGLE:
            self._take_over_bill(draft.bill_number)
        else:
            expect(self._invoice_number_field).to_be_hidden()
            self._ok_button.click()

    def _take_over_bill(self, bill_number: str) -> None:
        labelled_input(self.page, "Bill No.").fill(bill_number)
        self._ok_button.click()
        self.feedback.wait_for_loader()
        items = self.page.locator("div.modal-content").filter(has=self.page.locator("app-modal"))
        select_all_items(self.page, items, items.get_by_role("button", name=OK_BUTTON))
        expect(self.page.locator("div.modal-content challanorder-item")).to_be_hidden()

    def _enter_batch_details(self, row: int, line: PurchaseLineItem) -> None:
        self.grid.pick_batch(row, line.batch)

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        self.grid.enter_rate(row, line.rate)
        self.grid.enter_discounts(row, line)

    def _confirm_save_prompt(self) -> None:
        self.feedback.wait_for_loader()
        self._press_save_in_prompt(SAVE_PROMPT_TIMEOUT_MS)

    @property
    def _bill_details_window(self) -> Locator:
        # The bill-details window is a custom element inside a modal; it has no role or label.
        return self.page.locator("div.modal-content").filter(has=self.page.locator("out-billdetails"))

    @property
    def _ok_button(self) -> Locator:
        return self._bill_details_window.get_by_role("button", name=OK_BUTTON)
