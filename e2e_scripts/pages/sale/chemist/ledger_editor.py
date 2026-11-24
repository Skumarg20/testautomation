"""Opens a ledger in the Ledger Master, shared by the ledger discount pages."""

from playwright.sync_api import Locator, Page

from pages.components.popup import Popup
from pages.components.whole_text import whole_text

LEDGER_STATION = "Others"


class LedgerEditor:
    def __init__(self, page: Page) -> None:
        self._page = page

    def open_ledger(self, ledger_name: str) -> None:
        self._page.keyboard.press("Alt+L")
        search = self._page.locator("#SearchBox").first
        search.click()
        search.press_sequentially(ledger_name)
        self._edit_button(ledger_name).click()

    def fill_station_if_empty(self) -> None:
        """The form needs a station to save; a station the ledger already has is kept, not overwritten."""
        station = self._page.locator("#ddlstation")
        if station.input_value().strip():
            return
        station.click()
        station.press_sequentially(LEDGER_STATION)
        suggestions = self._page.locator('ngb-typeahead-window.dropdown-menu[role="listbox"]')
        suggestions.locator("button.dropdown-item", has_text=LEDGER_STATION).click()

    def open_others_tab(self) -> None:
        tabs = self._page.locator("ul.nav.nav-tabs.option02")
        tabs.locator("a").filter(has_text="Others").click()

    def save_and_confirm(self) -> None:
        self._page.locator("#btn-Update").click()
        self._page.wait_for_load_state("load")
        Popup(self._page).expect_shown_then_dismissed("Record updated successfully.")

    def _edit_button(self, ledger_name: str) -> Locator:
        name_cell = self._page.locator('[col-id="LedgerName"]').filter(has_text=whole_text(ledger_name))
        row = self._page.get_by_role("row").filter(has=name_cell)
        return row.locator('[col-id="1"]').locator("button.mksBtn.edit")
