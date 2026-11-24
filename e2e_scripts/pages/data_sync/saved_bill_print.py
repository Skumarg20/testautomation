"""A sale bill saved online, then its print window's WhatsApp tried offline (J35 DS-11).

After the save window the app opens the print window (`trxn-print`, `trxnprint.component.ts:22`) with a
`marg-button` "Whatsapp" (`trxnprint.component.html:81`). Its handler (`trxnprint.component.ts:527-720`)
ends in `Common.service.ts:4397-4401` `SendWhatsappMsg`, which reads `navigator.onLine` and warns
"Internet Required for this option!". Before that it may look up the WhatsApp usage (`GetSmsHistoryByuserID`),
which fails offline. The bill is the sales journey's stored case (as DS-04); the test deletes it afterwards.
DRAFT: written from the Angular source, not seen live.
"""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.data_sync.offline_bill import OfflineBill
from pages.sale.documents.bill import SaleBillDocument

SIGNED_OUT_ROUTE = re.compile(r"/(error|login)(?:[/?#]|$)")
WHATSAPP = re.compile(r"^\s*Whatsapp\s*$", re.IGNORECASE)
PRINT_WINDOW_TIMEOUT_MS = 60_000
# Why CSS: the print window is a component host with no role or heading of its own.
PRINT_WINDOW = "trxn-print"


class SavedBillPrint(BasePage):
    def save_new_bill(self) -> str:
        """Fills and saves the stored bill online; returns its number for the clean-up."""
        OfflineBill(self.page).fill()
        bill = SaleBillDocument(self.page)
        number = bill.document_number()
        bill.save()
        bill.confirm_save_window()
        expect(self._print_window).to_be_visible(timeout=PRINT_WINDOW_TIMEOUT_MS)
        return number

    def click_whatsapp(self) -> None:
        self._print_window.get_by_role("button", name=WHATSAPP).click()

    def is_signed_in(self) -> bool:
        """False once the app went to `/error` or `/login` (a call failed offline and the session ended)."""
        return not SIGNED_OUT_ROUTE.search(self.page.url)

    def delete_bill(self, number: str) -> None:
        """Deletes the bill from the list; call online and signed in."""
        bill = SaleBillDocument(self.page)
        if self._print_window.is_visible():
            bill.leave_to_list()
        bill.delete(number)

    @property
    def _print_window(self) -> Locator:
        return self.page.locator(PRINT_WINDOW)
