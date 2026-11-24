"""Report "Closing Stock Valuation" (`/report/profitloss/closingstock`, ClosingStock.html, not seen live):
one of the report screens whose toolbar is the generic import/export button (`marg-import-export-button`). Its
"Export" asks for a file name and type ("Export" dialog, save.as.component.html), then refuses an empty
report with "Exporting data not found !" (importexport.component.ts:281-295).
"""

import re

from playwright.sync_api import Download, Locator, expect

from pages.base_page import BasePage
from pages.components.downloads import collect_downloads
from pages.notifications_export.emptied_report import EmptiedReport

PATH = "/report/profitloss/closingstock"
TITLE = "Closing Stock Valuation"
LOAD_TIMEOUT_MS = 60_000
DIALOG_TIMEOUT_MS = 15_000
STOCK_ROWS = re.compile(r"Reports/GetOpeningClosingStock", re.IGNORECASE)
# The grid reads ClosingStock; the export's empty check reads ReportData (ClosingStock.ts:84-104).
ROW_KEYS = ("ClosingStock", "ReportData")


class ClosingStockPage(BasePage):
    def open_without_rows(self) -> None:
        EmptiedReport(self.page, STOCK_ROWS).serve_without(ROW_KEYS)
        with self.page.expect_response(STOCK_ROWS, timeout=LOAD_TIMEOUT_MS):
            self.goto(PATH, LOAD_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=TITLE)).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def export(self) -> list[Download]:
        """Export > Save in the file dialog, without waiting for a file. The returned list fills with any
        downloads that follow."""
        downloads = collect_downloads(self.page)
        self.page.get_by_title("Export", exact=True).click()
        expect(self._export_dialog).to_be_visible(timeout=DIALOG_TIMEOUT_MS)
        self._export_dialog.get_by_role("button", name=re.compile(r"Save$")).click()  # "F10 Save"
        return downloads

    @property
    def _export_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has=self.page.get_by_text("File Name"))
