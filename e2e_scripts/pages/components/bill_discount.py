"""The bill-level discount fields under the grid. They exist only while the setting switches are on."""

from decimal import Decimal

from playwright.sync_api import Locator

from pages.base_page import BasePage


class BillDiscount(BasePage):
    def enter_percent1(self, percent: Decimal) -> None:
        self._enter("billDiscountInPercent", percent)

    def enter_percent2(self, percent: Decimal) -> None:
        self._enter("billDiscountInPercent2", percent)

    def enter_amount(self, amount: Decimal) -> None:
        self._enter("billDiscountInAmount", amount)

    def _enter(self, form_control_name: str, value: Decimal) -> None:
        field = self._field(form_control_name)
        field.click()
        field.fill("")  # The masked input ignores Ctrl+A, so typing would append to the old value.
        self.page.keyboard.type(str(value))
        self.page.keyboard.press("Tab")

    def _field(self, form_control_name: str) -> Locator:
        return self.page.locator(f'[formcontrolname="{form_control_name}"]')
