"""The sale bill list's Email and Whatsapp buttons (`processout.list.component.html:54-58`).

Email shows for one or more selected bills, Whatsapp only for exactly one. Email on a bill whose party has
no e-mail id warns "Email Not Verified" (processout.list.component.ts:1655-1658, :1395; global.ts:19525);
more than one bill on Whatsapp warns "Only One Bill Can Be Send On Whatsapp" (:1486, global.ts:19366).
"""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.screen import DocumentScreen, tick_every_row

ROWS_TIMEOUT_MS = 60_000
EMAIL_BUTTON = re.compile(r"Email", re.IGNORECASE)
WHATSAPP_BUTTON = re.compile(r"Whatsapp", re.IGNORECASE)
EMAIL_NOT_VERIFIED = re.compile(r"Email Not Verified", re.IGNORECASE)
ONLY_ONE_ON_WHATSAPP = re.compile(r"Only One Bill Can Be Send On Whatsapp", re.IGNORECASE)


class SaleBillListShare(BasePage):
    def open_for(self, party: str) -> None:
        screen = DocumentScreen(self.page)
        screen.open_menu(SaleBillDocument.menu)
        expect(self._rows.first).to_be_visible(timeout=ROWS_TIMEOUT_MS)
        screen.search_list(party)
        expect(self._rows.first).to_be_visible(timeout=ROWS_TIMEOUT_MS)

    def select_every_bill(self) -> None:
        tick_every_row(self.page.locator("ag-grid-angular").first)

    def select_first_bill(self) -> None:
        # Why a class: ag-Grid draws the row's selection box as an icon only.
        self._rows.first.locator(".ag-icon-checkbox-unchecked").first.click()

    def press_email(self) -> None:
        self.email_button.click()

    def press_whatsapp(self) -> None:
        self.whatsapp_button.click()

    @property
    def email_button(self) -> Locator:
        return self.page.get_by_role("button", name=EMAIL_BUTTON)

    @property
    def whatsapp_button(self) -> Locator:
        return self.page.get_by_role("button", name=WHATSAPP_BUTTON)

    @property
    def _rows(self) -> Locator:
        return self.page.locator('[ref="eBodyContainer"] .ag-row')
