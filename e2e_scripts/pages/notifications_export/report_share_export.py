"""Export and share on a report screen with the Print Configuration step (the ledger report, live 2026-10-12).

Excel and PDF open "Print Configuration"; its only action ("Print") shows once "Configure" is ticked,
with the view "Current View" chosen by default. Share opens a menu: What's App > PDF, Email > Excel/PDF, SMS.
"""

import re

from playwright.sync_api import Download, Locator, expect

from pages.base_page import BasePage
from pages.notifications_export.json_route import fulfil_with_data

CONFIGURATION_TITLE = "Print Configuration"
CURRENT_VIEW = "Current View"
EXPORT_TIMEOUT_MS = 60_000
DIALOG_TIMEOUT_MS = 15_000
WHATSAPP_DIALOG_TITLE = "Share on Whatsapp"
WHATSAPP_NUMBER_LABEL = "WhatsApp Number"
# The upload that turns a report into a short link before WhatsApp sharing (MrgHttpService.service.ts).
SHARE_UPLOAD = re.compile(r"Common/(GetMediaLink|GetReporExceltLink)", re.IGNORECASE)
PDF_REPORT = re.compile(r"Common/GetReportData", re.IGNORECASE)


class ReportShareExport(BasePage):
    def stub_share_upload(self, link_id: str) -> None:
        """Answers the share upload with `link_id`, so no report file is stored for sharing."""
        self.page.route(SHARE_UPLOAD, lambda route: fulfil_with_data(route, link_id))

    def export_excel_current_view(self) -> Download:
        self.page.get_by_role("link", name="Excel", exact=True).click()
        print_button = self._configured_print_button()
        with self.page.expect_download(timeout=EXPORT_TIMEOUT_MS) as download:
            print_button.click()
        return download.value

    def export_pdf_current_view(self) -> bytes:
        """PDF > Configure > Print. Returns the file the server built (Common/GetReportData); the app opens
        it in a new tab, which headless Chromium leaves at about:blank."""
        self.page.get_by_role("link", name="PDF", exact=True).click()
        print_button = self._configured_print_button()
        with self.page.expect_response(PDF_REPORT, timeout=EXPORT_TIMEOUT_MS) as response:
            print_button.click()
        return response.value.body()

    def expect_no_export_icons(self) -> None:
        """A role without the Export right sees no Excel or PDF icon on the toolbar."""
        for icon in ("Excel", "PDF"):
            expect(self.page.get_by_role("link", name=icon, exact=True)).to_have_count(0)

    def email_pdf(self) -> None:
        """Share > Email > PDF; on a report with its own mail template this opens the "New Email" draft."""
        self._open_share_submenu("Email")
        self._visible_share_entry("PDF").click()

    def share_pdf_on_whatsapp(self) -> None:
        self._open_share_submenu("What's App")
        self._visible_share_entry("PDF").click()

    def expect_whatsapp_number_asked(self) -> None:
        dialog = self._whatsapp_dialog
        expect(dialog).to_be_visible(timeout=DIALOG_TIMEOUT_MS)
        expect(dialog.get_by_text(WHATSAPP_NUMBER_LABEL)).to_be_visible()

    def share_with_whatsapp_number(self, number: str) -> None:
        """Types the number into the "Share on Whatsapp" dialog and presses Share (F10)."""
        # Why an id: the number box has the label text beside it but no label element (transactionsms-qr).
        self._whatsapp_dialog.locator("#mobileno").fill(number)
        self._whatsapp_dialog.get_by_title("Share", exact=True).click()

    def close_whatsapp_dialog(self) -> None:
        # Why an id: the dialog's Close button is the app's marg-button with no accessible name.
        self._whatsapp_dialog.locator("#btnEsc").click()
        expect(self._whatsapp_dialog).to_be_hidden(timeout=DIALOG_TIMEOUT_MS)

    def _configured_print_button(self) -> Locator:
        dialog = self.page.get_by_role("dialog").filter(has_text=CONFIGURATION_TITLE)
        expect(dialog).to_be_visible(timeout=DIALOG_TIMEOUT_MS)
        # Why a value: the box has no label of its own, and the Trial Balance window adds Account Group,
        # Debit and Credit boxes beside it.
        dialog.locator('input[type="checkbox"][value="Configure"]').check()
        expect(dialog.get_by_role("option", name=CURRENT_VIEW, selected=True)).to_be_attached()
        return dialog.get_by_role("button", name="Print", exact=True)

    def _open_share_submenu(self, entry_title: str) -> None:
        self._share_menu.get_by_title("Share", exact=True).click()
        self._share_menu.get_by_title(entry_title, exact=True).hover()

    def _visible_share_entry(self, title: str) -> Locator:
        # The submenus of What's App and Email both have an entry titled "PDF"; only the hovered one shows.
        return self._share_menu.get_by_title(title, exact=True).filter(visible=True).first

    @property
    def _share_menu(self) -> Locator:
        # Why CSS: the Share button and its menu sit in a bare dropdown span; the toolbar beside it also
        # has icons titled "Excel" and "PDF", so the menu must be told apart from the toolbar.
        return self.page.locator("span.dropdown").filter(has=self.page.get_by_title("Share", exact=True))

    @property
    def _whatsapp_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text=WHATSAPP_DIALOG_TITLE)
