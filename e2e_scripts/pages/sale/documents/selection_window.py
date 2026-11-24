"""The searchable pick-list window the app opens for parties, patients, doctors, products and batches."""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.screen import exact_text, is_shown_within
from pages.stock.search_typing import type_search

RESULT_TIMEOUT_MS = 90_000
WINDOW_WAIT_MS = 3_000
# The item window searches Description unless told otherwise; picking by code needs its Itemcode mode.
SEARCH_MODES = {"itemcode": "Itemcode"}


class SelectionWindow(BasePage):
    def is_shown(self) -> bool:
        return is_shown_within(self._window, WINDOW_WAIT_MS)

    def choose_cell_value(self, value: str) -> None:
        """Pick the first list cell whose whole text is `value`."""
        self._search_then_click(
            value, self._window.locator(".ag-cell-value").filter(has_text=exact_text(value))
        )

    def choose_in_column(self, column: str, value: str) -> None:
        if column in SEARCH_MODES:
            self._window.get_by_role("combobox").first.select_option(SEARCH_MODES[column])
        cell = self.page.locator(f'[col-id="{column}"]').filter(has_text=exact_text(value))
        self._search_then_click(value, cell)

    def close(self) -> None:
        self._window.get_by_text("×").first.click()

    @property
    def _window(self) -> Locator:
        # Bootstrap modal markup; the window has no role or test id.
        return self.page.locator("div.modal-dialog.modal-lg")

    def _search_then_click(self, value: str, target: Locator) -> None:
        # Retyped when the list re-renders under the typing and drops keys (seen: "4" left of "44646015").
        type_search(self._window.get_by_role("searchbox"), value)
        expect(target.first).to_be_visible(timeout=RESULT_TIMEOUT_MS)
        target.first.click()
        expect(target).to_have_count(0, timeout=RESULT_TIMEOUT_MS)
