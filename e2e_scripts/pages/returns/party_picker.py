"""Purchase bill and return screens for a tenant that opens the "Select Party" window by itself.

Seen live 2026-10-08: the QA tenant opens the party picker as soon as Create/F2 is pressed. The shared
`PurchaseEntryForm.choose_vendor` clicks the Party Name field first, which the open picker covers, so it
times out. The mixin chooses the party in the window that is already open and otherwise leaves the shared
behaviour alone (the shared module belongs to the purchase journey and is not changed here).
"""

from playwright.sync_api import Page

from pages.purchase.documents import seed_documents
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.entry_form import VENDOR_CLOSED_TIMEOUT_MS, PurchaseEntryForm
from pages.purchase.documents.return_page import PurchaseReturnPage
from pages.purchase.documents.seed_documents import SeededBill


class OpenPartyPicker(PurchaseEntryForm):
    def choose_vendor(self, name: str) -> None:
        self.feedback.wait_for_loader()
        if not (name and self.vendor_window.is_open()):
            super().choose_vendor(name)
            return
        self.vendor_window.choose_cell_text(name)
        self.vendor_window.expect_closed(VENDOR_CLOSED_TIMEOUT_MS)


class PickerFirstPurchaseBillPage(OpenPartyPicker, PurchaseBillEntryPage):
    """Purchase > Bill (not the garments bill of `pages.purchase.garments`) on a picker-first tenant."""


class PurchaseReturnScreen(OpenPartyPicker, PurchaseReturnPage):
    pass


def seed_bill(page: Page) -> SeededBill:
    """`seed_documents.seed_bill` (Cash Account, standard line, new batch), via the bill above."""
    return seed_documents.seed_bill(page, PickerFirstPurchaseBillPage)
