"""Print and Export on the purchase bill list (sheet rows 51 and 52).

The list's toolbar buttons are handled in transactionin.list.component.ts: Print opens the Print window of the
selected bill (:1218-1265, `PrintBills` :2166, window with Preview / Close / Print as in
pages/notifications_export/bill_preview.py), Export runs `ExportSaleBilldata` (:1292-1294) and the file
arrives as a browser download. Button names and the export dialog are from the source and unverified live.
"""

import re

from playwright.sync_api import Download, Locator, expect

from pages.base_page import BasePage
from pages.purchase.documents.document_list import DocumentList
from pages.purchase.documents.feedback import appears_within

PRINT_WINDOW_TIMEOUT_MS = 30_000
EXPORT_DIALOG_MS = 5_000
EXPORT_FILE_MS = 30_000
SAVE_BUTTON = re.compile(r"Save$")


class BillListActions(BasePage):
    def print_window_for(self, number: str) -> Locator:
        """Selects the bill's row and presses Print; returns the Print window's Preview button."""
        DocumentList(self.page).row(number).click()
        self.page.get_by_role("button", name=re.compile(r"^\s*Print\b")).first.click()
        window = self.page.get_by_role("button", name=re.compile("Preview"))
        expect(window).to_be_visible(timeout=PRINT_WINDOW_TIMEOUT_MS)
        return window

    def close_print_window(self) -> None:
        self.page.locator("div.modal-header.p-2").get_by_text("×").click()

    def export_selected(self, number: str) -> Download:
        """Selects the bill's row and presses Export (and Save in the file-name dialog when it asks)."""
        DocumentList(self.page).row(number).click()
        with self.page.expect_download(timeout=EXPORT_FILE_MS) as download:
            self.page.get_by_role("button", name=re.compile(r"^\s*Export\b")).first.click()
            dialog = self.page.get_by_role("dialog").filter(has=self.page.get_by_text("File Name"))
            if appears_within(dialog, EXPORT_DIALOG_MS):
                dialog.get_by_role("button", name=SAVE_BUTTON).click()
        return download.value
