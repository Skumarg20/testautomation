"""Chemist > Create Prescription Master (`/chemist/prescription-create`, prescription.master.component.html,
not seen live). Pres. Date starts at today; "Pres. for Days" sets when the prescription falls due. The
patient is chosen in a selection window that its "---Search Here---" button opens; one item line is needed
or Save says the prescription details are missing (prescription.master.component.ts:1540-1543).
"""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.components.app_texts import RECORD_SAVED

PATH = "/chemist/prescription-create"
TITLE = re.compile(r"Create\s+Prescription Master")
LOAD_TIMEOUT_MS = 60_000
WINDOW_TIMEOUT_MS = 15_000
SEARCH_HERE = "---Search Here---"
ITEM_COLUMN = "itemLinkID"


class PrescriptionMasterPage(BasePage):
    def open_new(self) -> None:
        self.goto(PATH, LOAD_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=TITLE, level=1)).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def enter_days(self, days: int) -> None:
        # Why an id: the box's label is a sibling div label without a `for`.
        self.page.locator("#txtPresForDay").fill(str(days))

    def choose_patient(self, name: str) -> None:
        """Opens the patient selection window, types the name to search and picks the match."""
        self.page.get_by_role("button", name=SEARCH_HERE).first.click()
        window = self.page.get_by_role("dialog")
        expect(window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        self.page.keyboard.type(name)
        self.page.keyboard.press("Enter")
        expect(window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)
        expect(self._patient_name).to_have_value(name, timeout=WINDOW_TIMEOUT_MS)

    def add_item(self, description: str) -> None:
        # Why col-id: the item grid is an ag-Grid; its first editable cell is known only by col-id.
        self.page.locator(f'#precription [col-id="{ITEM_COLUMN}"]').first.click()
        self.page.keyboard.type(description)
        self.page.keyboard.press("Enter")

    def save(self) -> None:
        self.page.get_by_role("button", name=re.compile(r"\bSave\b")).first.click()
        Toasts(self.page).expect_any_saying(RECORD_SAVED, LOAD_TIMEOUT_MS)

    @property
    def _patient_name(self) -> Locator:
        # Why CSS: the read-only name box has no label element; only its form control name.
        return self.page.locator('input[formcontrolname="patientName"]')
