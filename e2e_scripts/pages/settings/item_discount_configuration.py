from typing import Literal

from pages.base_page import BasePage
from pages.components.app_texts import CONTROL_ROOM_SETTING_TITLE

VolumeDiscountType = Literal["Percentage", " Lumpsum ", " perUnit "]


class ItemDiscountConfiguration(BasePage):
    def set_volume_discount_types(self, first: VolumeDiscountType, second: VolumeDiscountType) -> None:
        self.page.locator("#aControlRoomSetting").click()
        self.page.locator("#sale-bill-discount").click()
        self.page.locator("#discount1").select_option(label=first)
        self.page.locator("#discount2").select_option(label=second)
        self.page.locator("#btn-Save").click()
        title = self.page.locator("h2.headingItem", has_text=CONTROL_ROOM_SETTING_TITLE)
        title.locator("button.close").click()
