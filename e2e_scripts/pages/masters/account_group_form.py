"""Master > Accounts Master > Group > Create/F2 and Edit/F3: the Create / Modify Account Group form."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.masters.master_list import AccountGroupList
from pages.masters.typeahead import Typeahead
from test_data.masters import AccountGroupSpec

SAVED_MESSAGE = re.compile("Record Saved Successfully", re.IGNORECASE)
UPDATED_MESSAGE = re.compile("Record Updated Successfully", re.IGNORECASE)
CREATE_HEADING = "Create Account Group"
FORM_TIMEOUT_MS = 30_000


class AccountGroupForm(BasePage):
    def open_new(self) -> None:
        AccountGroupList(self.page).open()
        self.page.keyboard.press("F2")
        expect(self._name).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def open_existing(self, name: str) -> None:
        groups = AccountGroupList(self.page)
        groups.open()
        groups.open_edit(name)
        expect(self._name).to_have_value(name, timeout=FORM_TIMEOUT_MS)

    def enter(self, group: AccountGroupSpec) -> None:
        self.enter_name(group.name)
        Typeahead(self.page).choose(self._parent, group.parent)

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def save(self) -> None:
        self.page.locator("#btn-Save").click()

    def update(self) -> None:
        self.page.locator("#btn-Update").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(UPDATED_MESSAGE)

    def expect_still_creating(self) -> None:
        expect(self.page.get_by_role("heading", name=CREATE_HEADING, level=1)).to_be_visible()
        expect(self._name).to_be_visible()

    def expect_parent(self, parent: str) -> None:
        expect(self._parent).to_have_value(parent, timeout=FORM_TIMEOUT_MS)

    @property
    def _name(self) -> Locator:
        # Why ids: the form has no test ids and its labels are not tied to the inputs.
        return self.page.locator("#txtGroupName")

    @property
    def _parent(self) -> Locator:
        return self.page.locator("#drpAccountGroup")
