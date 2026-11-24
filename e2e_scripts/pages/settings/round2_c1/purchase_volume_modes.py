"""Purchase Bill Setting > "Ask Bill Discount & Item Discount on Billing" > Configure: Purchase volume
discounts.

The Configure button (`#loss`, purchaseBill.setting.html:70-77) opens ControlRoomSettingSaleBillDiscount
(purchaseBill.setting.ts:303-306), whose Purchase column holds `#PurchaseVolumdiscount1` and
`#PurchaseVolumdiscount2` (sale-bill-discount-setting.html:138-165). Both lists are VolumDiscount1stType:
"perUnit / No / Lumpsum / Percentage" (lookup type 1025), so "Weight" is not offered on a purchase bill.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from pages.base_page import BasePage
from pages.components.app_texts import CONTROL_ROOM_SETTING_TITLE

MODES = ("perUnit", "No", "Lumpsum", "Percentage")
FIRST = "#PurchaseVolumdiscount1"
SECOND = "#PurchaseVolumdiscount2"


class PurchaseVolumeModes(BasePage):
    def current(self) -> tuple[str, str]:
        self._open()
        modes = (self._chosen(FIRST), self._chosen(SECOND))
        self._close()
        return modes

    def apply(self, first: str, second: str) -> None:
        self._open()
        self.page.locator(FIRST).select_option(label=first)
        self.page.locator(SECOND).select_option(label=second)
        self.page.locator("#btn-Save").click()
        self._close()

    def _chosen(self, selector: str) -> str:
        # Why CSS: a select exposes its chosen option only through :checked.
        return self.page.locator(selector).locator("option:checked").inner_text().strip()

    def _open(self) -> None:
        self.page.locator("#aControlRoomSetting").locator("visible=true").first.click()
        self.page.locator("#loss").click()

    def _close(self) -> None:
        title = self.page.locator("h2.headingItem", has_text=CONTROL_ROOM_SETTING_TITLE)
        title.locator("button.close").click()


@contextmanager
def purchase_modes_held(modes: PurchaseVolumeModes, wanted: tuple[str, str]) -> Iterator[None]:
    original = modes.current()
    try:
        modes.apply(*wanted)
        yield
    finally:
        modes.apply(*original)
