"""Control Room settings (global switches for the tenant). Changing one affects every later test."""

from typing import Literal

from playwright.sync_api import Locator, Page

from pages.base_page import BasePage

BarcodeRequired = Literal["Master wise", "Batch wise", "Multiple"]
LedgerCategory = Literal["Retailer", "Distributors", "Stockist", "Others"]
DateBilling = Literal[
    "Sale BackDate Billing",
    "Sale Future Date Billing",
    "Purchase BackDate Billing",
    "Purchase Future Date Billing",
]
YesNo = Literal["Yes", "No"]


class ControlRoom(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.open_button = page.locator("#aControlRoomSetting")
        self.configure_button = page.locator("#btnGStHeading-2")
        self.search = page.get_by_role("searchbox", name="Search", exact=True)
        self.save_button = page.locator("#btn-x")
        self.confirm_buttons = page.locator("#btnYes")

    def set_barcode_required(self, value: BarcodeRequired) -> None:
        self._set_option("Barcode Required", value)

    def set_date_billing(self, setting: DateBilling, value: YesNo) -> None:
        self._set_option(setting, value)

    def set_ledger_category(self, value: LedgerCategory) -> None:
        self._set_option("Ledger category", value)

    def set_switch(self, name: str, value: YesNo) -> None:
        """Any Yes/No option, by its full Particulars text (unique in the Control Room list)."""
        self._set_option(name, value)

    def _set_option(self, name: str, value: str) -> None:
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(name)
        self._dropdown_for(name).select_option(value)
        self.save_button.click()
        self.confirm_buttons.first.click()
        self.confirm_buttons.last.click()
        self.page.wait_for_load_state("load")

    def _dropdown_for(self, name: str) -> Locator:
        return self.page.locator(".row.m-0", has_text=name).first.locator("select")
