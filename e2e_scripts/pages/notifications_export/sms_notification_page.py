"""Report "SMS Notification" (`/support/sms-notification`, live 2026-10-12): the sent-SMS log of the
signed-in user, with the Excel, PDF and print icons of the shared export toolbar."""

import re
from contextlib import suppress

from playwright.sync_api import Download, Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from pages.components.downloads import collect_downloads
from pages.notifications_export.json_route import fulfil_with_data

PATH = "/support/sms-notification"
TITLE = "SMS Notification"
LOAD_TIMEOUT_MS = 60_000
EXPORT_TIMEOUT_MS = 60_000
SMS_HISTORY = re.compile(r"RegisterUser/GetSmsHistoryByuserID", re.IGNORECASE)
PDF_REPORT = re.compile(r"Common/GetReportData", re.IGNORECASE)
COMBINED_REPORT_PATH = re.compile(r"/report/combine-report/")
# Exports are rate limited to 2 calls a second (CommonController.cs:331); a second file comes within seconds.
SECOND_FILE_WINDOW_MS = 10_000
ANY_TEXT = re.compile(r"\S")


class SmsNotificationPage(BasePage):
    def serve_empty_log(self) -> None:
        """Answers the log call with no messages, so the report is empty whatever the user has sent.
        Call before `open`."""
        self.page.route(SMS_HISTORY, lambda route: fulfil_with_data(route, []))

    def open(self) -> None:
        with self.page.expect_response(SMS_HISTORY, timeout=LOAD_TIMEOUT_MS):
            self.goto(PATH, LOAD_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=TITLE, level=1)).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def expect_columns(self, columns: tuple[str, ...]) -> None:
        expect(self._grid.get_by_role("columnheader")).to_have_text(list(columns))

    def expect_period(self, period: re.Pattern[str]) -> None:
        expect(self.page.get_by_role("main").get_by_text(period)).to_be_visible()

    def grid_row_count(self) -> int:
        return self._message_rows.count()

    def logged_messages(self) -> list[str]:
        """The text of each message row, in screen order."""
        return [" ".join(text.split()) for text in self._message_rows.all_inner_texts()]

    def export_excel(self) -> Download:
        with self.page.expect_download(timeout=EXPORT_TIMEOUT_MS) as download:
            self._excel.click()
        return download.value

    def files_from_double_click_on_excel(self) -> int:
        """Double-clicks Excel and counts the files that arrive: the first, and any second one within the
        window the rate limit allows."""
        downloads = collect_downloads(self.page)
        with self.page.expect_download(timeout=EXPORT_TIMEOUT_MS):
            self._excel.dblclick()
        with suppress(PlaywrightTimeoutError):
            self.page.wait_for_event("download", timeout=SECOND_FILE_WINDOW_MS)
        return len(downloads)

    def click_excel(self) -> list[Download]:
        """Clicks Excel without waiting for a file. The returned list fills with any downloads that follow."""
        downloads = collect_downloads(self.page)
        self._excel.click()
        return downloads

    def expect_message(self, message: re.Pattern[str]) -> None:
        expect(self.page.get_by_text(message)).to_be_visible(timeout=EXPORT_TIMEOUT_MS)

    def export_pdf(self) -> bytes:
        """Clicks PDF; the app opens a new tab for the file. Returns the file the server built."""
        return self._pdf_from(self.page.get_by_role("link", name="PDF", exact=True))

    def print_report(self) -> bytes:
        # Why CSS: the print icon is the toolbar's only link without a title, so it has no accessible name.
        return self._pdf_from(self.page.locator("sharedexportimport a:not([title])"))

    def go_back(self) -> None:
        self.page.get_by_role("link", name="Back").click()
        expect(self.page).to_have_url(COMBINED_REPORT_PATH, timeout=LOAD_TIMEOUT_MS)

    def _pdf_from(self, icon: Locator) -> bytes:
        with (
            self.page.context.expect_page(timeout=EXPORT_TIMEOUT_MS),
            self.page.expect_response(PDF_REPORT, timeout=EXPORT_TIMEOUT_MS) as response,
        ):
            icon.click()
        return response.value.body()

    @property
    def _excel(self) -> Locator:
        return self.page.get_by_role("link", name="Excel", exact=True)

    @property
    def _message_rows(self) -> Locator:
        """Rows that hold a message; the grid pads itself with empty rows."""
        return self._grid.get_by_role("row").filter(
            has=self.page.get_by_role("gridcell").filter(has_text=ANY_TEXT)
        )

    @property
    def _grid(self) -> Locator:
        return self.page.get_by_role("main").get_by_role("grid")
