"""Finds and selects the company kept for data sync requests that cannot be undone (J35 DS-18, DS-19, DS-45).

See `test_data/data_sync.py`. The organisation list (`/user-company`) lists each company in an ag-Grid
`compname` column (as `pages/company_switch_page.py`).
"""

import re

from playwright.sync_api import Locator

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.company_switch_page import CompanySwitchPage

LIST_TIMEOUT_MS = 30_000
# Why CSS: ag-Grid cells have no accessible name; the column id is the grid's only stable handle.
COMPANY_NAME_CELL = '[col-id="compname"]'


class ThrowawayCompany(BasePage):
    def is_listed(self, name: str) -> bool:
        CompanySwitchPage(self.page).open()
        return appears_within(self._name_cell(name), LIST_TIMEOUT_MS)

    def select(self, name: str) -> None:
        CompanySwitchPage(self.page).ensure_company(name)

    def _name_cell(self, name: str) -> Locator:
        return self.page.locator(COMPANY_NAME_CELL).filter(has_text=re.compile(rf"^\s*{re.escape(name)}\s*$"))
