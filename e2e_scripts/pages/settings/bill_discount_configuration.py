"""Sale Bill Setting > "Ask Bill Discount & Item Discount on Billing" > Configure (Sale column)."""

from dataclasses import dataclass

from pages.base_page import BasePage
from pages.components.app_texts import CONTROL_ROOM_SETTING_TITLE


@dataclass(frozen=True)
class BillDiscountSwitches:
    discount1: bool = False
    discount2: bool = False
    in_amount: bool = False


class BillDiscountConfiguration(BasePage):
    def current_switches(self) -> BillDiscountSwitches:
        self._open_configuration()
        switches = BillDiscountSwitches(
            self._is_on("billDiscountSale"),
            self._is_on("billdiscount2Sale"),
            self._is_on("saleBillDiscountInAmount"),
        )
        self._save_and_close()
        return switches

    def apply(self, switches: BillDiscountSwitches) -> None:
        self._open_configuration()
        self._set("billDiscountSale", switches.discount1)
        self._set("billdiscount2Sale", switches.discount2)
        self._set("saleBillDiscountInAmount", switches.in_amount)
        self._save_and_close()

    def _open_configuration(self) -> None:
        self.page.locator("#aControlRoomSetting").click()
        self.page.locator("#sale-bill-discount").click()

    def _is_on(self, switch_id: str) -> bool:
        return self.page.locator(f"#{switch_id}").is_checked()

    def _set(self, switch_id: str, on: bool) -> None:
        self.page.locator(f"#{switch_id}").set_checked(on)

    def _save_and_close(self) -> None:
        self.page.locator("#btn-Save").click()
        title = self.page.locator("h2.headingItem", has_text=CONTROL_ROOM_SETTING_TITLE)
        title.locator("button.close").click()
