"""Previews a saved sale bill once per print format offered in its Print window.

After a save the app opens "Print" (trxnprint.component.html:22-29): `#format` lists the company's templates
(`templatename || name`), Preview posts the bill to `PrintTemplate/PrintTemplateExport` (or
`Reports/InvoiceExport`) and opens the PDF (trxnprint.component.ts:322-386). Nothing goes to a printer.
"""

from playwright.sync_api import Locator

from pages.base_page import BasePage
from pages.notifications_export.bill_preview import BILL_PDF, PREVIEW, PREVIEW_TIMEOUT_MS
from pages.sale.documents.bill import SaleBillDocument

WINDOW = "#billDetailForm"


class PrintFormats(BasePage):
    def __init__(self, bill: SaleBillDocument) -> None:
        super().__init__(bill.page)
        self._bill = bill
        self.pdfs: dict[str, bytes] = {}

    def save_and_preview_every_format(self) -> None:
        """Saves the open bill, previews it in each format, and leaves to the list."""
        self._bill.save()
        self._bill.confirm_save_window()
        self._bill.screen.wait_for_loader()
        formats = self._window.locator("#format")
        names = [text.strip() for text in formats.locator("option").all_inner_texts()]
        for name in names:
            formats.select_option(label=name)
            with self.page.expect_response(BILL_PDF, timeout=PREVIEW_TIMEOUT_MS) as response:
                self._window.get_by_role("button", name=PREVIEW).click()
            self.pdfs[name] = response.value.body()
        self._bill.leave_to_list()

    @property
    def _window(self) -> Locator:
        return self.page.locator(WINDOW)
