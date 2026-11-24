"""The sale bill a converted own-store order opens (`/transaction`), as the J37 conversion tests read it.

Built on the shared sale-bill page objects; only what the conversion scenarios need is added here:
- the invoice value (`.bill-value-text`, the figure `InvoiceTotals` reads),
- the party and the customer's "Mobile No." in the header (`UI/Transaction/InverntoryTransaction/
  processout.transaction.component.html:222-228`; the mobile row shows only for chemist companies or when
  "Customer Name" is on in the Control Room),
- deleting an item line: Delete on a selected row asks "Do you want to delete this Item- <name>?"
  (`processout.transaction.component.ts:9385-9400, 15234-15238`),
- reopening a saved bill with the list's row action "Modify" (as `screen.row_action` does for Delete).
Not seen live (spec "To verify live").
"""

from decimal import Decimal

from playwright.sync_api import expect

from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.document_requests import last_number
from pages.sale.documents.header import DocumentHeader
from pages.sale.documents.item_grid import AMOUNT, DocumentItemGrid
from pages.sale.documents.screen import DocumentScreen

TRANSACTION_URL = "**/transaction"
BILL_TIMEOUT_MS = 60_000
PARTY_LABEL = "Party Name"
MOBILE_LABEL = "Mobile No."
DELETE_LINE_QUESTION = "Do you want to delete this"
MODIFY_ACTION = "Modify"


class ConvertedBill(BasePage):
    def expect_open(self) -> None:
        self.page.wait_for_url(TRANSACTION_URL, timeout=BILL_TIMEOUT_MS)
        DocumentScreen(self.page).wait_for_loader()

    def invoice_value(self) -> Decimal:
        # Why CSS: the invoice value is a plain span with no role or label (as in InvoiceTotals).
        value = self.page.locator(".bill-value-text").first
        expect(value).to_be_visible(timeout=BILL_TIMEOUT_MS)
        return last_number(value.inner_text())

    def party_name(self) -> str:
        return DocumentHeader(self.page).field(PARTY_LABEL).input_value()

    def customer_mobile(self) -> str:
        return DocumentHeader(self.page).field(MOBILE_LABEL).input_value()

    def delete_line(self, row: int) -> None:
        """Selects the row by its read-only amount cell, presses Delete and confirms."""
        DocumentItemGrid(self.page).cell(row, AMOUNT).click()
        self.page.keyboard.press("Delete")
        dialog = ConfirmDialog(self.page)
        dialog.expect_asking(DELETE_LINE_QUESTION)
        dialog.answer_yes()

    def reopen(self, number: str) -> None:
        """Opens the saved bill again for modification from Sale > Bill's list."""
        bill = SaleBillDocument(self.page)
        bill.screen.open_menu(bill.menu)
        bill.screen.search_list(number)
        bill.screen.row_action(number, MODIFY_ACTION)
        self.expect_open()
