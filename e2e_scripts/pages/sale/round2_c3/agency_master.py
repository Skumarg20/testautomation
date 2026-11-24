"""Master > Inventory Master > Agency: create an agency (optionally prohibited) and delete it again.

Written from the source: the list is `UI/Master/Agency/itemcompanymaster.component.html`, the form
`add.itemcompany.component.html` with `#txtCName` (agency name, :37-41) and the Prohibit drop-down
`#drpProhibit` (:195-206, options from `typeData`, Yes / No). The sidebar entry is "Inventory Master > Agency"
(menumaster.json). Save / Create / Delete buttons follow the other masters (`MasterList`). Unverified live.
"""

import re

from playwright.sync_api import Page, expect

from pages.accounting.accounting_menu import MASTER_GROUP, AccountingMenu
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.masters.master_list import LIST_TIMEOUT_MS, MasterList

AGENCY_PATH = ("Inventory Master", "Agency")
SAVED_MESSAGE = re.compile("Record Saved Successfully", re.IGNORECASE)
FORM_TIMEOUT_MS = 30_000


class AgencyList(MasterList):
    def open(self) -> None:
        AccountingMenu(self.page)._open(MASTER_GROUP, AGENCY_PATH)
        expect(self.page.get_by_role("button", name="Create/F2")).to_be_visible(timeout=LIST_TIMEOUT_MS)


class AgencyMaster(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._names: list[str] = []

    def create(self, name: str, prohibited: bool) -> None:
        """Creates the agency; it is remembered first so a half-done save is still cleaned up."""
        self._names.append(name)
        AgencyList(self.page).open()
        self.page.get_by_role("button", name="Create/F2").click()
        field = self.page.locator("#txtCName")
        expect(field).to_be_visible(timeout=FORM_TIMEOUT_MS)
        field.fill(name)
        self.page.locator("#drpProhibit").select_option(label="Yes" if prohibited else "No")
        self.page.get_by_role("button", name=re.compile("Save")).first.click()
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)

    def delete_all(self) -> None:
        agencies = AgencyList(self.page)
        for name in reversed(self._names):
            agencies.open()
            if agencies.is_listed(name):
                agencies.delete(name)
        self._names.clear()
