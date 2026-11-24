"""Sale Bill Setting > Sale Bill Discount window (`#sale-bill-discount`): how the volume discounts are taken.

The modes are the ones `dataCalculation.ts:437-480` computes: Percentage (of the line amount), Lumpsum (the
value itself) and perUnit (the value times the quantity). `ItemDiscountConfiguration` only writes; this class
reads the first mode too, so a test can put the original back. The window opens from the settings icon of an
open sale bill, as `ItemDiscountConfiguration` does.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import Page, expect

from pages.base_page import BasePage
from pages.components.app_texts import CONTROL_ROOM_SETTING_TITLE
from pages.settings.item_discount_configuration import ItemDiscountConfiguration, VolumeDiscountType

WINDOW_TIMEOUT_MS = 15_000
OPTIONS: tuple[VolumeDiscountType, ...] = ("Percentage", " Lumpsum ", " perUnit ")


class UnknownVolumeDiscountModeError(ValueError):
    def __init__(self, text: str) -> None:
        super().__init__(f"Unknown volume discount mode {text!r}; known: {OPTIONS}")


class VolumeDiscountModes(BasePage):
    def current(self) -> tuple[VolumeDiscountType, VolumeDiscountType]:
        self.page.locator("#aControlRoomSetting").click()
        self.page.locator("#sale-bill-discount").click()
        expect(self.page.locator("#discount1")).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        modes = (self._chosen("#discount1"), self._chosen("#discount2"))
        self.page.locator("h2.headingItem", has_text=CONTROL_ROOM_SETTING_TITLE).locator(
            "button.close"
        ).click()
        return modes

    def set_first(self, mode: VolumeDiscountType) -> None:
        """The second mode is kept as it is."""
        second = self.current()[1]
        ItemDiscountConfiguration(self.page).set_volume_discount_types(mode, second)

    def _chosen(self, selector: str) -> VolumeDiscountType:
        # Why CSS: a select exposes its chosen option only through the :checked state.
        text = self.page.locator(selector).locator("option:checked").inner_text()
        for known in OPTIONS:
            if known.strip().lower() == text.strip().lower():
                return known
        raise UnknownVolumeDiscountModeError(text)


@contextmanager
def first_volume_discount_held(page: Page, mode: VolumeDiscountType) -> Iterator[None]:
    modes = VolumeDiscountModes(page)
    original = modes.current()[0]
    modes.set_first(mode)
    try:
        yield
    finally:
        modes.set_first(original)
