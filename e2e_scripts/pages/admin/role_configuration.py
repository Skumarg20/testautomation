"""The "Role Configurations" dialog: role name, description and the rights grid per menu."""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from test_data.user_roles import Right

DIALOG_TIMEOUT_MS = 30_000
SAVE_TIMEOUT_MS = 60_000
# Why a class: the empty mandatory name shows only an icon; Angular marks the input ng-invalid.
NG_INVALID = re.compile(r"\bng-invalid\b")


class RoleConfiguration(BasePage):
    def expect_open(self) -> None:
        expect(self._dialog).to_be_visible(timeout=DIALOG_TIMEOUT_MS)

    def fill_name(self, name: str) -> None:
        self._name.fill(name)

    def fill_description(self, description: str) -> None:
        self._description.fill(description)

    def grant_full(self, right: Right) -> None:
        self._show_menu(right.menu)
        self._full_checkbox(right).check()

    def save(self) -> None:
        self._dialog.get_by_role("button", name="F10 Save").click()

    def update(self) -> None:
        self._dialog.get_by_role("button", name="F10 Update").click()

    def close(self) -> None:
        self._dialog.get_by_role("button", name="Esc Close").click()
        expect(self._dialog).to_be_hidden(timeout=DIALOG_TIMEOUT_MS)

    def expect_closed(self) -> None:
        expect(self._dialog).to_be_hidden(timeout=SAVE_TIMEOUT_MS)

    def expect_shows(self, name: str, description: str) -> None:
        expect(self._name).to_have_value(name, timeout=DIALOG_TIMEOUT_MS)
        expect(self._description).to_have_value(description)

    def expect_full_granted(self, right: Right) -> None:
        self._show_menu(right.menu)
        expect(self._full_checkbox(right)).to_be_checked(timeout=DIALOG_TIMEOUT_MS)

    def expect_every_right_checked(self, right: Right) -> None:
        """Full, Create, Edit, Delete and Export (as many columns as the menu's grid has)."""
        self._show_menu(right.menu)
        checkboxes = self._rights_row(right).get_by_role("checkbox")
        expect(checkboxes.first).to_be_visible(timeout=DIALOG_TIMEOUT_MS)
        for checkbox in checkboxes.all():
            expect(checkbox).to_be_checked()

    def expect_name_rejected(self) -> None:
        """The empty mandatory name is flagged and the dialog stays open; the app shows no message text."""
        expect(self._name).to_have_class(NG_INVALID, timeout=DIALOG_TIMEOUT_MS)
        expect(self._dialog).to_be_visible()

    def _show_menu(self, menu: str) -> None:
        self._dialog.get_by_role("link", name=menu, exact=True).click()

    def _full_checkbox(self, right: Right) -> Locator:
        return self._rights_row(right).get_by_role("checkbox").first

    def _rights_row(self, right: Right) -> Locator:
        return self._dialog.get_by_role("row", name=right.name, exact=True)

    @property
    def _dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name="Role Configurations")
        )

    @property
    def _name(self) -> Locator:
        # Why an id: the "Role *" label is a bare text node not tied to its input.
        return self._dialog.locator("#txtrolenamep")

    @property
    def _description(self) -> Locator:
        return self._dialog.locator("#txtdescription")
