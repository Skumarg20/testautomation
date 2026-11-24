"""The list screens of Master > Accounts Master (Ledger Master, Account Group List): search, edit, delete."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.inventory.item_alert import ItemAlert
from pages.masters.masters_menu import MastersMenu

# Case-blind: the DOM text is lower case and CSS capitalises it on screen.
DELETED_MESSAGE = re.compile("Record Deleted Successfully", re.IGNORECASE)
DELETE_QUESTION = "Are you sure you want to delete the selected Record?"
LIST_TIMEOUT_MS = 60_000
ROW_TIMEOUT_MS = 30_000
PRESENCE_LOOKUP_MS = 5_000


class MasterList(BasePage):
    def open(self) -> None:
        raise NotImplementedError

    def expect_listed(self, name: str) -> None:
        self.search(name)
        expect(self._row(name)).to_have_count(1, timeout=ROW_TIMEOUT_MS)

    def expect_not_listed(self, name: str) -> None:
        self.search(name)
        expect(self._row(name)).to_have_count(0, timeout=ROW_TIMEOUT_MS)

    def is_listed(self, name: str) -> bool:
        self.search(name)
        return appears_within(self._row(name), PRESENCE_LOOKUP_MS)

    def open_edit(self, name: str) -> None:
        self.search(name)
        self._row(name).get_by_role("button", name="Edit/F3").click()

    def ask_to_delete(self, name: str) -> None:
        self.search(name)
        self._row(name).get_by_role("button", name="Delete").click()

    def confirm_delete(self) -> None:
        alert = ItemAlert(self.page)
        alert.expect_asking(DELETE_QUESTION)
        alert.answer_yes()

    def delete(self, name: str) -> None:
        self.ask_to_delete(name)
        self.confirm_delete()
        Toasts(self.page).expect_success_saying(DELETED_MESSAGE)

    def search(self, name: str) -> None:
        """The search moves matching rows to the top; it does not hide the others."""
        self._search_box.fill(name)

    def _wait_until_loaded(self) -> None:
        expect(self._search_box).to_be_visible(timeout=LIST_TIMEOUT_MS)
        expect(self.page.get_by_role("gridcell").first).to_be_visible(timeout=LIST_TIMEOUT_MS)

    @property
    def _search_box(self) -> Locator:
        return self.page.get_by_role("searchbox", name="Search", exact=True)

    def _row(self, name: str) -> Locator:
        name_cell = self.page.get_by_role("gridcell", name=name, exact=True)
        return self.page.get_by_role("row").filter(has=name_cell)


class LedgerList(MasterList):
    def open(self) -> None:
        MastersMenu(self.page).open_ledger_list()
        self._wait_until_loaded()

    def open_outstanding(self, name: str) -> None:
        """F8 on a selected ledger opens its bill-wise outstanding (outstanding.report.ts:410)."""
        self.search(name)
        self.page.get_by_role("gridcell", name=name, exact=True).first.click()
        self.page.keyboard.press("F8")

    def station_of(self, name: str) -> Locator:
        self.search(name)
        # Why col-id: the grid is an ag-Grid; its cells are told apart only by col-id.
        return self._row(name).locator('[col-id="cus_Station"]')


class AccountGroupList(MasterList):
    def open(self) -> None:
        MastersMenu(self.page).open_account_group_list()
        self._wait_until_loaded()

    def names_in_view(self, name: str) -> list[str]:
        """The tree rows shown for a search: the matching group and the chain of groups above it."""
        self.search(name)
        expect(self._row(name)).to_have_count(1, timeout=ROW_TIMEOUT_MS)
        # Why col-id: the name column of the tree grid.
        cells = self.page.get_by_role("gridcell").and_(self.page.locator('[col-id="name"]'))
        return [text.strip() for text in cells.all_inner_texts()]
