"""A filled sale bill whose save is attempted while the browser is offline (J35 DS-04, DS-05).

The bill is the sales journey's stored case TC_SM_009 on the pharma company (item 3, batch BATCH001), built
with the same steps the sales tests use. No guard covers the bill save itself
(`processout.transaction.component.ts:830-844` sets `noInternetConnection`, the save path never reads it):
the pointer is stopped only by the overlay (`app.component.ts:29-30`), the keyboard is not stopped at all.
DRAFT: the save keys and windows come from the sales page objects; the offline outcome is not seen live.
"""

import re

from playwright.sync_api import Page, expect

from pages.components.footer import Footer
from pages.data_sync.maintenance_page import TITLE as MAINTENANCE_TITLE
from pages.sale.documents.bill import SaleBillDocument, press_end_until_saving
from pages.sale.documents.document_requests import request_from
from pages.sale.documents.flows import STORED_BILL, fill_body, start_document, stored_case

SAVE_ENDPOINT = re.compile(r"BillSales/Save|TempBillHold/Save", re.IGNORECASE)
SAVE_OUTCOME_TIMEOUT_MS = 30_000
SAVE_WINDOW_BUTTON = "save"


class OfflineBill:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._bill = SaleBillDocument(page)

    def fill(self) -> None:
        request = request_from(stored_case("bill", STORED_BILL))
        start_document(self._bill, request)
        fill_body(self._bill, request)

    @property
    def page(self) -> Page:
        return self._page

    def number(self) -> str:
        """The bill number the open form shows (the next number of the series until it is saved)."""
        return self._bill.document_number()

    def click_save(self) -> None:
        """A real pointer click where Save is: whatever lies on top at that point receives it.

        `force` only skips Playwright's wait for the button to be the top element; without it the call
        would time out on the overlay instead of letting the overlay take the click as a user's would.
        """
        Footer(self._page).save_button.click(force=True)

    def save_with_keyboard(self) -> None:
        """End starts the save; the save window's own button is then pressed with Enter, not the pointer."""
        press_end_until_saving(self._page)
        save_window = self._bill.save_window
        maintenance = self._page.get_by_role("heading", name=MAINTENANCE_TITLE)
        expect(save_window.or_(maintenance).first).to_be_visible(timeout=SAVE_OUTCOME_TIMEOUT_MS)
        if save_window.is_visible():
            save_window.get_by_role("button", name=SAVE_WINDOW_BUTTON).focus()
            self._page.keyboard.press("Enter")

    def expect_still_open(self) -> None:
        expect(Footer(self._page).save_button).to_be_visible()
