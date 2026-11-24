"""Master > Inventory Master > HSN / SAC > Create/F2 and Edit/F3: the Create / Modify HSN/SAC dialog."""

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.components.app_texts import RECORD_SAVED, RECORD_UPDATED
from pages.unit_hsn.master_lists import HsnList
from test_data.unit_hsn import HsnSpec

FORM_TIMEOUT_MS = 30_000


class HsnForm(BasePage):
    def open_new(self) -> None:
        HsnList(self.page).open()
        self.page.keyboard.press("F2")
        expect(self._code).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def open_existing(self, code: str) -> None:
        codes = HsnList(self.page)
        codes.open()
        codes.open_edit(code)
        expect(self._code).to_have_value(code, timeout=FORM_TIMEOUT_MS)

    def enter(self, hsn: HsnSpec) -> None:
        self.enter_code(hsn.code)
        self.enter_name(hsn.name)

    def enter_code(self, code: str) -> None:
        self._code.fill(code)

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def save(self) -> None:
        self.page.locator("#btn-Save").click()

    def update(self) -> None:
        self.page.locator("#btn-Update").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(RECORD_SAVED)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(RECORD_UPDATED)

    @property
    def _code(self) -> Locator:
        # Why ids: the dialog has no test ids and its labels are not tied to the inputs.
        return self.page.locator("#inphsncode")

    @property
    def _name(self) -> Locator:
        return self.page.locator("#inphsnname")
