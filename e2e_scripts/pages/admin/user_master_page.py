"""User List (/mstr/usermaster): the All Users tab with "Invite User" and the Roles tab with its role grid."""

import re

from playwright.sync_api import Locator, expect

from pages.admin.role_configuration import RoleConfiguration
from pages.base_page import BasePage

PAGE_TIMEOUT_MS = 120_000
MESSAGE_TIMEOUT_MS = 30_000
ROLE_SAVED = "Role Saved Successfully"
ROLE_DELETED = "Delete Successfully"
DELETE_QUESTION = "Do you want to delete selected role ?"
PREDEFINED_REFUSAL = "Sorry, Pre-Defined Roles Can't Be Deletable Or Editable, Clone The Role Instead"
SEAT_LIMIT_ALERT = re.compile(r"Allowed (\d+) users only")


class UserMasterPage(BasePage):
    PATH = "/mstr/usermaster"

    def open_users(self) -> None:
        self.page.goto(self.PATH, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        expect(self._invite_user).to_be_visible(timeout=PAGE_TIMEOUT_MS)
        expect(self._listed_rows.first).to_be_visible(timeout=PAGE_TIMEOUT_MS)

    def open_roles(self) -> None:
        self.open_users()
        self.page.get_by_role("tab", name="Roles").click()
        expect(self.page.get_by_role("columnheader", name="Description")).to_be_visible(
            timeout=PAGE_TIMEOUT_MS
        )
        expect(self._listed_rows.first).to_be_visible(timeout=PAGE_TIMEOUT_MS)

    def start_new_role(self) -> RoleConfiguration:
        self.page.get_by_role("button", name="Create", exact=True).click()
        configuration = RoleConfiguration(self.page)
        configuration.expect_open()
        return configuration

    def edit_role(self, name: str) -> RoleConfiguration:
        """Selects the row first: the action icons act on the grid's selected row (see `click_edit_icon`)."""
        self._select(name)
        return self.click_edit_icon(name)

    def click_edit_icon(self, name: str) -> RoleConfiguration:
        self._role_row(name).first.get_by_role("button", name="Edit/F3").click()
        return RoleConfiguration(self.page)

    def ask_to_delete_role(self, name: str) -> None:
        self._select(name)
        self._role_row(name).first.get_by_role("button", name="Delete").click()

    def delete_role(self, name: str) -> None:
        self.ask_to_delete_role(name)
        question = self.page.get_by_role("dialog").filter(has_text=DELETE_QUESTION)
        # Why the text: both answer buttons are named "Close" (aria-label); only their text differs.
        question.get_by_role("button").filter(has_text="Yes").click()
        self.expect_message(ROLE_DELETED)

    def role_count(self, name: str) -> int:
        return self._role_row(name).count()

    def expect_role_listed(self, name: str, description: str) -> None:
        row = self._role_row(name)
        expect(row).to_have_count(1, timeout=MESSAGE_TIMEOUT_MS)
        expect(row.get_by_role("gridcell", name=description, exact=True)).to_be_visible()

    def expect_role_not_listed(self, name: str) -> None:
        expect(self._role_row(name)).to_have_count(0, timeout=MESSAGE_TIMEOUT_MS)

    def expect_message(self, text: str) -> None:
        # Case-blind: the toast's DOM text differs in case from what CSS shows on screen.
        message = re.compile(f"^{re.escape(text)}$", re.IGNORECASE)
        expect(self.page.get_by_text(message).first).to_be_visible(timeout=MESSAGE_TIMEOUT_MS)

    def invite_user(self) -> None:
        self._invite_user.click()

    def user_count(self) -> int:
        """Users listed on All Users; ag-Grid also renders empty filler rows, which have no name."""
        return self._listed_rows.count()

    def expect_seat_limit_alert(self, seats: int) -> None:
        alert = self.page.get_by_role("dialog").filter(has_text=SEAT_LIMIT_ALERT)
        expect(alert).to_be_visible(timeout=MESSAGE_TIMEOUT_MS)
        expect(alert.get_by_text(SEAT_LIMIT_ALERT)).to_have_text(f"Allowed {seats} users only")

    def _select(self, name: str) -> None:
        self._role_row(name).first.get_by_role("gridcell", name=name, exact=True).click()

    def _role_row(self, name: str) -> Locator:
        name_cell = self.page.get_by_role("gridcell", name=name, exact=True)
        return self.page.get_by_role("row").filter(has=name_cell)

    @property
    def _listed_rows(self) -> Locator:
        """Rows with a serial number; the grid pads itself with empty rows."""
        serial = self.page.get_by_role("gridcell", name=re.compile(r"^\d+$"))
        return self.page.get_by_role("row").filter(has=serial)

    @property
    def _invite_user(self) -> Locator:
        return self.page.get_by_role("button", name="Invite User")
