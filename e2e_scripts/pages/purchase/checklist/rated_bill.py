"""A purchase bill that types its own MRP and sale rate A into the Batch Details window.

The ordinary bill fills both with the line's purchase rate (`enter_sale_prices`). Here they are chosen, so a
test can see the item master follow the last batch's rates (sheet row 48).
"""

from decimal import Decimal

from playwright.sync_api import Page

from pages.purchase.checklist.batch_details_window import BatchDetailsWindow
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.line_items import PurchaseLineItem


class RatedPurchaseBill(PurchaseBillEntryPage):
    def __init__(self, page: Page, mrp: Decimal, rate_a: Decimal) -> None:
        super().__init__(page)
        self._mrp = mrp
        self._rate_a = rate_a

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        PurchaseEntryForm._enter_price_details(self, row, line)
        window = BatchDetailsWindow(self.page)
        window.expect_open()
        window.fill_and_close(self._mrp, self._rate_a)
