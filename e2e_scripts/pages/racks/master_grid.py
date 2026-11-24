"""The Store List and Rack List grids: search, find a row, edit and delete it."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.confirmation import Confirmation
from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.inventory.item_alert import ItemAlert

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
DELETED_MESSAGE = re.compile("Record Deleted Successfully", re.IGNORECASE)
LIST_TIMEOUT_MS = 60_000
ROW_TIMEOUT_MS = 30_000
PRESENCE_LOOKUP_MS = 5_000
CONFIRM_LOOKUP_MS = 5_000
SEARCH_KEY_DELAY_MS = 50


class MasterGrid(BasePage):
    """A list screen with a "Search" box, one row per record and Edit/Delete buttons on each row."""

    delete_question = ""

    def open(self) -> None:
        raise NotImplementedError

    def expect_listed(self, name: str) -> None:
        self.search(name)
        expect(self._row(name)).to_have_count(1, timeout=ROW_TIMEOUT_MS)

    def expect_not_listed(self, name: str) -> None:
        if self._is_empty():
            return
        self.search(name)
        expect(self._row(name)).to_have_count(0, timeout=ROW_TIMEOUT_MS)

    def is_listed(self, name: str) -> bool:
        if self._is_empty():
            return False
        self.search(name)
        return appears_within(self._row(name), PRESENCE_LOOKUP_MS)

    def open_edit(self, name: str) -> None:
        self.search(name)
        self._row(name).get_by_role("button", name=re.compile("Edit")).click()

    def ask_to_delete(self, name: str) -> None:
        self.search(name)
        self._row(name).first.get_by_role("button", name="Delete").click()

    def try_to_delete(self, name: str) -> None:
        """Answers Yes if the app asks; for deletes of own records that the app is expected to refuse."""
        self.ask_to_delete(name)
        Confirmation(self.page).answer_yes_if_asked(CONFIRM_LOOKUP_MS)

    def delete(self, name: str) -> None:
        self.ask_to_delete(name)
        alert = ItemAlert(self.page)
        alert.expect_asking(self.delete_question)
        alert.answer_yes()
        Toasts(self.page).expect_success_saying(DELETED_MESSAGE)

    def search(self, name: str) -> None:
        """Typed key by key: the grid filters on key events."""
        self._search_box.click()
        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(name, delay=SEARCH_KEY_DELAY_MS)

    def _wait_until_loaded(self) -> None:
        """Either the grid with its search box, or the empty page that has neither."""
        expect(self._search_box.or_(self._empty_heading)).to_be_visible(timeout=LIST_TIMEOUT_MS)
        if not self._is_empty():
            expect(self.page.get_by_role("gridcell").first).to_be_visible(timeout=LIST_TIMEOUT_MS)

    def _is_empty(self) -> bool:
        return self._empty_heading.is_visible()

    @property
    def _empty_heading(self) -> Locator:
        """Shown instead of the grid when the company has no record, e.g. "No Rack Created Yet"."""
        return self.page.get_by_role("heading", name=re.compile(r"^No .* Created Yet$"), level=2)

    @property
    def _search_box(self) -> Locator:
        return self.page.get_by_role("searchbox", name="Search", exact=True)

    def _row(self, name: str) -> Locator:
        name_cell = self.page.get_by_role("gridcell", name=name, exact=True)
        return self.page.get_by_role("row").filter(has=name_cell)
