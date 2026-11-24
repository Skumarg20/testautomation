"""Item rates (A to H) in the Item Master, and the bill's default billing rate setting."""

from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.components.app_texts import RECORD_UPDATED
from pages.components.whole_text import whole_text

RATE_LABELS = {letter: f"{letter.upper()}-Rate" for letter in "abcdefgh"}
ITEM_SEARCH_TIMEOUT_MS = 20_000


class RateValidationPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._setting_search = page.locator("input#controlRoomSearchField")

    def change_item_rate(self, item: str, rate_letter: str, amount: Decimal | int) -> None:
        """Writes the rate on the item named exactly `item`; the item list is shared, so no other row."""
        self.page.keyboard.press("Alt+I")
        self._setting_search.fill(item)
        edit = self._item_row(item).locator("action button")
        expect(edit).to_have_count(1, timeout=ITEM_SEARCH_TIMEOUT_MS)
        edit.click()
        expect(self.page.locator("#txtProduct")).to_have_value(whole_text(item, ignore_case=True))
        rate_field = self.page.locator(f'input[formcontrolname="rate{rate_letter}"]')
        rate_field.fill(format(Decimal(amount), "f"))
        self.page.locator("#btnSave").click()
        Toasts(self.page).expect_success_saying(RECORD_UPDATED)

    def set_default_billing_rate(self, rate_letter: str) -> None:
        self.page.locator("#aControlRoomSetting").click()
        self.page.locator("tabs ul li").last.click()
        self._setting_search.click()
        self._setting_search.press_sequentially("Default Billing Rate")
        self.page.locator("#DefaultBillingRate").select_option(label=RATE_LABELS[rate_letter])
        title = self.page.locator("h2.headingItem", has_text="Sale Bill Setting")
        title.locator("button.close").click()

    def _item_row(self, item: str) -> Locator:
        name_cell = self.page.get_by_role("gridcell").filter(has_text=whole_text(item, ignore_case=True))
        return self.page.get_by_role("row").filter(has=name_cell)
