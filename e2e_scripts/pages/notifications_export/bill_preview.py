"""A sale bill saved through the outstanding journey's desk, previewed in its Print window before the window
is closed.

After a save the app opens "Print" (trxnprint.component.html: Select Format, Preview, Close, Print, Whatsapp).
Preview posts the bill to `PrintTemplate/PrintTemplateExport` (or `Reports/InvoiceExport` for the built-in
format) and opens the PDF in a new tab (trxnprint.component.ts:322-386). Nothing goes to a printer.
The desk's own save path is reused unchanged; only its last step, closing the Print window, also previews.
"""

import re
from decimal import Decimal

from playwright.sync_api import Page

from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.sale.documents.screen import is_shown_within

BILL_PDF = re.compile(r"(PrintTemplate/PrintTemplateExport|Reports/InvoiceExport)", re.IGNORECASE)
PREVIEW = re.compile(r"Preview")
PREVIEW_TIMEOUT_MS = 60_000
PRINT_LOOKUP_MS = 10_000


class PreviewNotOfferedError(AssertionError):
    def __init__(self) -> None:
        super().__init__("The Print window after the sale bill save showed no Preview button")


class PreviewedSaleBillDesk(SaleBillDesk):
    def __init__(self, page: Page, item: str) -> None:
        super().__init__(page, item)
        self.preview = b""

    def create_unpaid(self, party: str, amount: Decimal) -> str:
        """Saves a credit bill for `amount`; `preview` then holds the PDF its Print window previewed."""
        return self.create(party, amount, Decimal(0))

    def _close_print_window(self) -> None:
        preview = self._print_window.get_by_role("button", name=PREVIEW)
        if not is_shown_within(preview, PRINT_LOOKUP_MS):
            raise PreviewNotOfferedError()
        with self._page.expect_response(BILL_PDF, timeout=PREVIEW_TIMEOUT_MS) as response:
            preview.click()
        self.preview = response.value.body()
        super()._close_print_window()
