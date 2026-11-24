"""Sale Bill Setting > Net Scheme > Configure: formula and Reverse Calculation.

asknetrate-setting.html: `#txtnetschemeFormula` (options 1..4), `#reverseCalculation` (Yes/No); the Configure
button shows only when Net Scheme is Yes (salebill.setting.html:243-249, id `netscheme`). The window closes
with Esc or F10 (asknetrate-setting.ts:75-80).
"""

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import expect

from pages.base_page import BasePage
from pages.components.app_texts import CONTROL_ROOM_SETTING_TITLE

WINDOW_TIMEOUT_MS = 15_000
ADVANCE_TAB_FIELD = "#netscheme"


class NetSchemeWindow(BasePage):
    def current(self) -> tuple[str, str]:
        self._open()
        values = (
            self.page.locator("#txtnetschemeFormula").input_value(),
            self.page.locator("#reverseCalculation").locator("option:checked").inner_text().strip(),
        )
        self._close()
        return values

    def apply(self, formula: str, reverse: str) -> None:
        self._open()
        self.page.locator("#txtnetschemeFormula").select_option(value=formula)
        self.page.locator("#reverseCalculation").select_option(label=reverse)
        self._close()

    def _open(self) -> None:
        self.page.locator("#aControlRoomSetting").locator("visible=true").first.click()
        self.page.locator(ADVANCE_TAB_FIELD).click()
        expect(self.page.locator("#txtnetschemeFormula")).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def _close(self) -> None:
        self.page.keyboard.press("F10")
        title = self.page.locator("h2.headingItem", has_text=CONTROL_ROOM_SETTING_TITLE)
        title.locator("button.close").click()


@contextmanager
def net_scheme_configured(window: NetSchemeWindow, formula: str, reverse: str) -> Iterator[None]:
    original = window.current()
    try:
        window.apply(formula, reverse)
        yield
    finally:
        window.apply(*original)
