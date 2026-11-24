"""Master > Inventory Master > Unit > Create/F2 and Edit/F3: the Create / Modify Unit dialog."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.unit_hsn.master_lists import UnitList
from test_data.unit_hsn import UnitSpec

# Case-blind: the DOM text is lower case and CSS capitalises it on screen.
SAVED_MESSAGE = re.compile("Data Saved Successfully", re.IGNORECASE)
UPDATED_MESSAGE = re.compile("Data Updated Successfully", re.IGNORECASE)
NAME_REQUIRED = "Unit name required !"
CREATE_HEADING = "Create Unit"
FORM_TIMEOUT_MS = 30_000
OPTIONS_TIMEOUT_MS = 5_000
UQC_ATTEMPTS = 3


class UqcNotOfferedError(AssertionError):
    def __init__(self, uqc: str) -> None:
        super().__init__(f'UQC "{uqc}" was not offered in the Create Unit list after {UQC_ATTEMPTS} tries')


class UnitForm(BasePage):
    def open_new(self) -> None:
        UnitList(self.page).open()
        self.page.keyboard.press("F2")
        expect(self._name).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def open_existing(self, name: str) -> None:
        units = UnitList(self.page)
        units.open()
        units.open_edit(name)
        expect(self._name).to_have_value(name, timeout=FORM_TIMEOUT_MS)

    def enter(self, unit: UnitSpec) -> None:
        self.enter_name(unit.name)
        self.choose_uqc(unit.uqc)

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def choose_uqc(self, uqc: str) -> None:
        """One key opens the full UQC list; typing more keys is unreliable, so the option is clicked."""
        option = self.page.get_by_role("listbox").get_by_role("option", name=uqc, exact=True)
        for _ in range(UQC_ATTEMPTS):
            self._uqc.fill("")
            self._uqc.press(uqc[0])
            if appears_within(option, OPTIONS_TIMEOUT_MS):
                option.click()
                expect(self._uqc).to_have_value(uqc)
                return
        raise UqcNotOfferedError(uqc)

    def save(self) -> None:
        self.page.locator("#btn-Save").click()

    def update(self) -> None:
        self.page.locator("#btn-Update").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(UPDATED_MESSAGE)

    def expect_name_required(self) -> None:
        expect(self.page.get_by_text(NAME_REQUIRED, exact=True)).to_be_visible()

    def expect_still_creating(self) -> None:
        expect(self.page.get_by_role("heading", name=CREATE_HEADING, level=5)).to_be_visible()
        expect(self._name).to_be_visible()

    def expect_uqc(self, uqc: str) -> None:
        expect(self._uqc).to_have_value(uqc, timeout=FORM_TIMEOUT_MS)

    @property
    def _name(self) -> Locator:
        # Why ids: the dialog has no test ids and its labels are not tied to the inputs.
        return self.page.locator("#txtUnitName")

    @property
    def _uqc(self) -> Locator:
        return self.page.locator("#addUnit")
