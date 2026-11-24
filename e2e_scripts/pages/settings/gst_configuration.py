from typing import Literal, cast

from playwright.sync_api import Locator

from pages.base_page import BasePage
from pages.components.app_texts import CONTROL_ROOM_SETTING_TITLE

GstType = Literal["Inclusive", "Exclusive", "Tax on MRP(inc.)"]


class GstConfiguration(BasePage):
    def current_gst_type(self) -> GstType:
        shown = self._open_calculation_type().get_by_role("option", selected=True).inner_text()
        self._close_setting_window()
        return cast(GstType, shown.strip())

    def select_gst_type(self, gst_type: GstType) -> None:
        self._open_calculation_type().select_option(label=gst_type)
        self._close_setting_window()

    def _open_calculation_type(self) -> Locator:
        self.page.locator("#aControlRoomSetting").click()
        dropdown = self.page.locator("#calculationTypeForSale")
        dropdown.wait_for(state="visible")
        return dropdown

    def _close_setting_window(self) -> None:
        title = self.page.locator("h2.headingItem", has_text=CONTROL_ROOM_SETTING_TITLE)
        title.locator("button.close").click()
