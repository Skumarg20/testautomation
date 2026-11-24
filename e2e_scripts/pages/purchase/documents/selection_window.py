"""The pop-up windows a purchase document opens: the item/party/batch picker and the pending-document list."""

import re
from enum import Enum

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback, appears_within
from pages.stock.search_typing import type_search

OPEN_TIMEOUT_MS = 2_000
PICK_TIMEOUT_MS = 90_000
CLOSE_TIMEOUT_MS = 50_000
ITEM_WINDOW_TIMEOUT_MS = 20_000
ITEM_CODE_COLUMN = "itemcode"
# The item window searches Description unless told otherwise.
ITEM_CODE_SEARCH_MODE = "Itemcode"
SAVE_BUTTON_ID_PREFIX = "btn-Save"


class SelectionWindow(BasePage):
    """Lists parties, items or batches; type in the search box, click the matching cell."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._feedback = AppFeedback(page)

    def is_open(self) -> bool:
        return appears_within(self._window, OPEN_TIMEOUT_MS)

    def choose_cell_text(self, text: str) -> None:
        self._search(text)
        self._click_and_wait_closed(
            self._window.locator(".modal-body .ag-cell-value").filter(has_text=_exactly(text))
        )

    def choose_item_code(self, code: str) -> None:
        self._window.get_by_role("combobox").first.select_option(ITEM_CODE_SEARCH_MODE)
        self._search(code)
        cell = self._window.locator(f'[col-id="{ITEM_CODE_COLUMN}"]').filter(has_text=_exactly(code))
        self._click_and_wait_closed(cell)

    def close_without_choosing(self) -> None:
        self.page.keyboard.press("Escape")

    def close_with_cross(self) -> None:
        self._cross.click()

    def expect_closed(self, timeout_ms: int) -> None:
        expect(self._window).to_be_hidden(timeout=timeout_ms)

    def cross_is_shown(self, timeout_ms: int) -> bool:
        return appears_within(self._cross, timeout_ms)

    @property
    def _cross(self) -> Locator:
        # Two different headers carry the cross, depending on how the window was opened.
        cross = "div#header-modal span[aria-hidden='true'], ngb-modal-window:not([aria-hidden='true']) button"
        return self.page.locator(cross).filter(has_text="×").first

    def _search(self, text: str) -> None:
        self._feedback.wait_for_loader()
        # Retyped when the list re-renders under the typing and drops keys.
        type_search(self._window.get_by_role("searchbox"), text)

    def _click_and_wait_closed(self, cell: Locator) -> None:
        expect(cell.first).to_be_visible(timeout=PICK_TIMEOUT_MS)
        cell.first.click()
        self._feedback.wait_for_loader()
        expect(cell.first).to_be_hidden(timeout=CLOSE_TIMEOUT_MS)

    @property
    def _window(self) -> Locator:
        # The picker is a large Bootstrap modal with no title or role of its own.
        return self.page.locator("div.modal-dialog.modal-lg")


class PendingKind(Enum):
    QUOTATION = "Pending Quotation"
    ORDER = "Pending Orders"
    CHALLAN = "Pending Challans"


class PendingDocumentWindow(BasePage):
    """The list of open quotations, orders or challans offered when a document is started for a party."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._feedback = AppFeedback(page)

    def is_open(self, kind: PendingKind, timeout_ms: int) -> bool:
        return appears_within(self._window(kind), timeout_ms)

    def close(self, kind: PendingKind) -> None:
        self._window(kind).locator("div.modal-header").get_by_text("×").click()

    def pull_in(self, kind: PendingKind, number: str) -> None:
        """Ticks the document, saves, then takes all of its items over into the new document."""
        window = self._window(kind)
        self._feedback.wait_for_loader()
        window.locator("#SearchBox").fill(number)
        self._row_checkbox(window, number).click()
        window.locator(f"button[id^={SAVE_BUTTON_ID_PREFIX}]").click()
        self._feedback.wait_for_loader()
        expect(window).to_be_hidden()
        items = self.page.locator("div.modal-content challanorder-item")
        select_all_items(self.page, items, items.locator(f"button[id^={SAVE_BUTTON_ID_PREFIX}]"))

    def _window(self, kind: PendingKind) -> Locator:
        return self.page.locator("div.modal-content pending-challan").filter(has_text=kind.value)

    @staticmethod
    def _row_checkbox(window: Locator, number: str) -> Locator:
        # ag-Grid draws its tick boxes as icon spans without a role.
        row = window.locator(".ag-row-position-absolute").filter(
            has=window.page.get_by_text(number, exact=True)
        )
        return row.locator("span.ag-icon-checkbox-unchecked").first


def select_all_items(page: Page, items_window: Locator, save_button: Locator) -> None:
    """In a window listing the items of a picked document, ticks every item and saves."""
    expect(items_window).to_be_visible(timeout=ITEM_WINDOW_TIMEOUT_MS)
    if not appears_within(items_window.locator("span.ag-checkbox-checked"), OPEN_TIMEOUT_MS):
        items_window.locator(".ag-header-select-all span.ag-icon").locator("visible=true").first.click()
    save_button.click()
    AppFeedback(page).confirm_if_asked()
    expect(items_window).to_be_hidden()


def _exactly(text: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*{re.escape(text)}\s*$", re.IGNORECASE)
