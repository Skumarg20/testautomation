"""A purchase bill whose new batch carries a deal (Batch Details `#txtscheme1` + `#txtscheme2`).

transactioninbatch.component.html:171-176 holds the two fields (Deal: buy + free); the sale bill
reads them when
"Free Deal From" is Batch (processout.transaction.component.ts:13433-13445).
"""

from playwright.sync_api import Locator, Page

from pages.purchase.checklist.batch_details_window import BatchDetailsWindow
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.line_items import PurchaseLineItem


class DealPurchaseBill(PurchaseBillEntryPage):
    def __init__(self, page: Page, deal: tuple[int, int]) -> None:
        super().__init__(page)
        self._deal = deal

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        PurchaseEntryForm._enter_price_details(self, row, line)
        window = BatchDetailsWindow(self.page)
        window.expect_open()
        window.type_mrp(line.rate)
        window.type_rate("a", line.rate)
        buy, free = self._deal
        self._field("#txtscheme1").fill(str(buy))
        self._field("#txtscheme2").fill(str(free))
        self.page.keyboard.press("Enter")

    def _field(self, selector: str) -> Locator:
        return self.page.locator("ngb-modal-window").filter(has_text="Batch Details").last.locator(selector)
