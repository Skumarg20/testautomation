"""Control Room > Configure > "Stock Negative" > Configure: the "Stock Setting" window.

Unlike the plain Yes/No rows, this option is set in its own window (stock-negative-setting.html): the select
`#negativeAllowed` ("Stock Negative allowed") and `#isGoingtoNegativeStock` ("Indicate if going in negative
stock"). F10 or the cross closes the window into the Control Room, whose Save then stores it. It implements
`SwitchAccess`, so `switch_held` (pages/settings/control_room_switch.py) reads it first and puts the original
back. The option texts are assumed to be "Yes"/"No" (the list comes from the API, `StockNegativeallowed`);
all locators are from the Angular source and unverified live (KB `careportal_enriched_v5.csv#117b8963`).
"""

from typing import cast, get_args

from playwright.sync_api import Locator, expect

from pages.settings.control_room import ControlRoom, YesNo
from pages.settings.control_room_state import UnexpectedOptionError

STOCK_NEGATIVE_ROW = "Stock Negative"
STOCK_NEGATIVE_ALLOWED = "Stock Negative allowed"
WINDOW_TIMEOUT_MS = 15_000
SELECT_FOR = {
    STOCK_NEGATIVE_ALLOWED: "#negativeAllowed",
    "Indicate if going in negative stock": "#isGoingtoNegativeStock",
}


class StockNegativeSetting(ControlRoom):
    def current_switch(self, name: str) -> YesNo:
        self._open_window()
        # Why CSS: a select exposes its chosen option only through the :checked state.
        text = self._select(name).locator("option:checked").inner_text().strip()
        self.page.keyboard.press("Escape")
        self.page.keyboard.press("Escape")
        if text not in get_args(YesNo):
            raise UnexpectedOptionError(name, text, get_args(YesNo))
        return cast(YesNo, text)

    def set_switch(self, name: str, value: YesNo) -> None:
        self._open_window()
        self._select(name).select_option(label=value)
        self.page.keyboard.press("F10")
        expect(self._window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)
        self.save_button.click()
        self.confirm_buttons.first.click()
        self.confirm_buttons.last.click()
        self.page.wait_for_load_state("load")

    def _open_window(self) -> None:
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(STOCK_NEGATIVE_ROW)
        row = self.page.locator(".row.m-0", has_text=STOCK_NEGATIVE_ROW).first
        row.get_by_role("button", name="Configure").click()
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def _select(self, name: str) -> Locator:
        return self._window.locator(SELECT_FOR[name])

    @property
    def _window(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name="Stock Setting")
        )
