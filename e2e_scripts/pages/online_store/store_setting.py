"""Online store settings: the Control Room "Store Setting" window and the dashboard's "Store Configuration".

- Control Room > Configure > "Store Setting" (bindCode 4409,
  `margerpmodel/Other/ControlRoomDesignData.cs:1361`) is a Yes/No row whose "Configure" button shows only
  while the row is Yes (`DynamicForm/form.component.html` fieldtype 4). The button opens
  `OnlineStoreSettingComponent` as a modal "Store Setting" (`form.component.ts:3431-3432`;
  `Master/OlineStoreSetting/online-store-setting.component.html`).
- The header Control Room on the order dashboard opens the panel "Store Configuration" instead
  (`Layout/homelayout.component.ts:1631-1632`;
  `UtililityComponent/ControlRoom/onlineStore.ControlRoom.Config.html`). Both offer only "Rate Selection"; the
  window has no Save button (its footer is commented out). Not seen live.
"""

from playwright.sync_api import Locator, expect

from pages.purchase.documents.feedback import AppFeedback
from pages.settings.control_room import ControlRoom
from test_data.online_store import RATE_SELECTION

STORE_SETTING_ROW = "Store Setting"
WINDOW_TITLE = "Store Setting"
PANEL_TITLE = "Store Configuration"
WINDOW_TIMEOUT_MS = 15_000
CROSS = "×"


class StoreSettingWindow(ControlRoom):
    def open(self) -> None:
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(STORE_SETTING_ROW)
        self._control_room_row().get_by_role("button", name="Configure").click()
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def column_headers(self) -> list[str]:
        return [text.strip() for text in self._window.get_by_role("columnheader").all_inner_texts()]

    def particulars(self) -> list[str]:
        """The Particulars cell of every body row, i.e. the settings the window offers."""
        rows = self._window.locator("tbody").get_by_role("row")
        return [row.get_by_role("cell").nth(1).inner_text().strip() for row in rows.all()]

    def rate_options(self) -> list[str]:
        return [text.strip() for text in self._rate_select.locator("option").all_inner_texts()]

    def chosen_rate(self) -> str:
        # Why CSS: a select exposes its chosen option only through the :checked state.
        return self._rate_select.locator("option:checked").inner_text().strip()

    def choose_rate(self, caption: str) -> None:
        self._rate_select.select_option(label=caption)

    @property
    def save_button_in_window(self) -> Locator:
        return self._window.get_by_role("button", name="Save")

    def close_with_cross(self) -> None:
        self._window.get_by_role("button", name=CROSS).click()

    def close_with_escape(self) -> None:
        self.page.keyboard.press("Escape")

    def expect_closed(self) -> None:
        expect(self._window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    def save_control_room(self) -> None:
        """The Control Room's own Save and its two confirmations, as `ControlRoom.set_switch` answers them."""
        self.save_button.click()
        self.confirm_buttons.first.click()
        self.confirm_buttons.last.click()
        self.page.wait_for_load_state("load")
        AppFeedback(self.page).wait_for_loader()

    def leave_control_room(self) -> None:
        """Escape closes the Control Room unchanged (as `ControlRoomState` leaves it)."""
        self.page.keyboard.press("Escape")

    @property
    def _window(self) -> Locator:
        title = self.page.get_by_role("heading", name=WINDOW_TITLE, exact=True)
        return self.page.get_by_role("dialog").filter(has=title)

    @property
    def _rate_select(self) -> Locator:
        return self._window.get_by_role("row").filter(has_text=RATE_SELECTION).get_by_role("combobox")

    def _control_room_row(self) -> Locator:
        # Why CSS: Control Room rows are plain divs; the same container `ControlRoom._dropdown_for` uses.
        return self.page.locator(".row.m-0", has_text=STORE_SETTING_ROW).first


class StoreConfigurationPanel(ControlRoom):
    """The header Control Room as it opens on the order dashboard."""

    def open(self) -> None:
        self.open_button.click()
        expect(self.page.get_by_role("heading", name=PANEL_TITLE)).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def rate_options(self) -> list[str]:
        # Why CSS: each option of the panel is a plain div.itemTitle with no role (Config.html:119-147).
        rate_row = self._panel.locator(".itemTitle").filter(has_text=RATE_SELECTION)
        return [text.strip() for text in rate_row.get_by_role("combobox").locator("option").all_inner_texts()]

    def text(self) -> str:
        return self._panel.inner_text()

    @property
    def _panel(self) -> Locator:
        # Why CSS: the panel is a plain div under an h2 (controlroom.setting.component.html:1-15), no role.
        return self.page.locator(".itemControl").filter(
            has=self.page.get_by_role("heading", name=PANEL_TITLE)
        )
