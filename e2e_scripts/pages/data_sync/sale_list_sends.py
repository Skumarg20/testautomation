"""Email, Upload Bills and WhatsApp on the sale bill list, each tried while offline (J35 DS-10).

`processout.list.component.ts:1305-1340`: Upload Bills checks `noInternetConnection` first; Email and
WhatsApp first await the invoice-layout and print-template lookups and check the flag after them (pack
correction: offline those lookups may fail with status 0 and send the app to `/error` before the guard).
Keys: Alt+E (Email, needs a ticked bill) and Alt+W (WhatsApp) reach the list behind the overlay
(`:2080-2091`); Upload has no key, only the `marg-button` "Upload" (`ButtonEnum.Upload`, `global.ts:18737`;
`buttons.component.ts:12-35` prints the enum text in the button).
DRAFT: written from the Angular source, not seen live.
"""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.sale.documents.bill import SaleBillDocument

UPLOAD = re.compile(r"^\s*Upload\s*$")
ROW_TIMEOUT_MS = 30_000
# Why CSS: the bill list is an ag-Grid; its row check boxes have no name (the grid's own selection class).
ROW_CHECKBOX = ".ag-center-cols-container .ag-row .ag-selection-checkbox"


class SaleListSends(BasePage):
    def open(self) -> None:
        bill = SaleBillDocument(self.page)
        bill.screen.open_menu(bill.menu)

    def has_a_bill(self) -> bool:
        return appears_within(self._row_checkboxes.first, ROW_TIMEOUT_MS)

    def tick_first_bill(self) -> None:
        self._row_checkboxes.first.click()

    def press_email(self) -> None:
        self.page.keyboard.press("Alt+E")

    def press_whatsapp(self) -> None:
        self.page.keyboard.press("Alt+W")

    def click_upload(self) -> None:
        upload = self.page.get_by_role("button", name=UPLOAD)
        expect(upload).to_be_visible()
        upload.click()

    @property
    def _row_checkboxes(self) -> Locator:
        return self.page.locator(ROW_CHECKBOX)
