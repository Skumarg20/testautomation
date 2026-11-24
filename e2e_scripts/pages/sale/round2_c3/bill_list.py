"""The Sale > Bill list and the Sale > Draft list, for bills a test saved itself.

Template: `UI/Transaction/InverntoryTransaction/processout.list.component.html`. With a row selected the list
shows Print, Email, Whatsapp (one bill only) and an Export drop-down (:33-86); the filter menu has Today,
This Week, ... and a Custom range with `txtfromDate`, `txttoDate` and `txtApply` (:123-185); each row has an
edit button and a menu (Delete, Logs, Cash Receive). The draft list is Sale > Draft (support article "How to
Draft Bill in Marg Books"). Unverified live: the date text format and the Export items.
"""

import re
from datetime import date

from playwright.sync_api import Download, Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.documents.dates import ENTRY_DATE_FORMAT
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.screen import DocumentScreen

DRAFT_MENU = ("Sale", "Draft")
DOWNLOAD_TIMEOUT_MS = 60_000
MENU_ITEMS = ("Delete", "Logs")


class SaleBillList(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.screen = DocumentScreen(page)

    def open(self) -> None:
        self.screen.open_menu(SaleBillDocument.menu)

    def find(self, text: str) -> Locator:
        self.screen.search_list(text)
        return self.screen.list_row(text)

    def select(self, number: str) -> None:
        # Why CSS: ag-Grid draws the row's tick box as an icon without a role (as pending_windows does).
        self.find(number).locator(".ag-icon-checkbox-unchecked").first.click()

    def button(self, name: str) -> Locator:
        return self.page.get_by_role("button", name=re.compile(name))

    def export_first_format(self) -> Download:
        """Opens the Export drop-down of the selected bill and takes its first format (kept local)."""
        toggle = self.page.locator("button.dropdown-toggle-split").first
        toggle.click()
        with self.page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as download:
            self.page.locator(".dropdown-menu.show .dropdown-item").first.click()
        return download.value

    def open_row_menu(self, number: str) -> Locator:
        row = self.find(number)
        row.locator('button[data-toggle="dropdown"]').click()
        return self.page.locator(".dropdown-menu.show")

    def apply_custom_range(self, first: date, last: date) -> None:
        self.page.locator("button.default-btn.dropdown-toggle").click()
        self.page.get_by_text("Custom", exact=True).click()
        self._type_date("txtfromDate", first)
        self._type_date("txttoDate", last)
        self.page.locator("#txtApply").click()
        self.screen.wait_for_loader()

    def _type_date(self, control_id: str, day: date) -> None:
        box = self.page.locator(f"#{control_id}")
        box.press("Control+A")
        box.press_sequentially(day.strftime(ENTRY_DATE_FORMAT))
        box.press("Tab")


class SaleDrafts(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.screen = DocumentScreen(page)

    def open(self) -> None:
        self.screen.open_menu(DRAFT_MENU)

    def expect_listed(self, party: str) -> None:
        self.screen.search_list(party)
        expect(self.screen.list_row(party)).to_be_visible()

    def delete(self, party: str) -> None:
        self.open()
        self.screen.delete_listed_record(party)
