"""Printing bills from the Sale > Bill list: tick the rows, press the toolbar Print button.

`processout.list.component.html:37-39` shows Print once a row is ticked; `buttonEvent(Print)` allows 1
to 5 bills
(more: "Only 5 Bills allowed at a time for Printing", global.ts:19372) and `getInvoicePrintData`
(Common.service.ts) posts the ticked bills' ids (`BillLinkIDs`) to the print-template export and opens the PDF
(Common.service.ts, `printBill(blobUrl)`). The PDF response is read; nothing reaches a printer.
"""

import re

from playwright.sync_api import Page, expect

from pages.accounting.outstanding.document_list import DocumentList
from pages.base_page import BasePage
from pages.notifications_export.bill_preview import BILL_PDF
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.screen import DocumentScreen

PRINT_TIMEOUT_MS = 60_000


class BillListPrint(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._screen = DocumentScreen(page)
        self._list = DocumentList(page, SaleBillDocument.menu)

    def print_bills(self, party: str, numbers: list[str]) -> bytes:
        """Ticks the bills' rows (listed by the party search) and returns the PDF the print button builds."""
        self._list.numbers_for(party)
        for number in numbers:
            row = self._screen.list_row(number)
            # Why CSS: the row-select box is ag-Grid's checkbox input; it has no label.
            row.locator(".ag-selection-checkbox input").check()
        button = self.page.get_by_role("button", name=re.compile(r"Print"))
        expect(button.first).to_be_visible(timeout=PRINT_TIMEOUT_MS)
        with self.page.expect_response(BILL_PDF, timeout=PRINT_TIMEOUT_MS) as response:
            button.first.click()
        return response.value.body()
