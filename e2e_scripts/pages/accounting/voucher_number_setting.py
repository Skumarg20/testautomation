"""Control Room switch "Voucher No. Required ?"; receipt and payment show a voucher number only if Yes."""

from playwright.sync_api import Locator

from pages.base_page import BasePage

SETTING_LABEL = "Voucher No. Required ?"
REQUIRED = "Yes"


class VoucherNumberSetting(BasePage):
    """Changes a tenant-wide setting: callers must run in the "chemist-tenant" xdist group."""

    def require_voucher_numbers(self) -> None:
        # Why ids and classes: the Control Room panel has no roles or test ids.
        self.page.locator("#aControlRoomSetting").click()
        self._dropdown.select_option(REQUIRED)
        self._close_button.click()

    @property
    def _dropdown(self) -> Locator:
        row = self.page.locator("div.row").filter(has_text=SETTING_LABEL)
        return row.get_by_role("combobox").first

    @property
    def _close_button(self) -> Locator:
        heading = self.page.locator("div.dashboardSetting h2.headingItem")
        return heading.get_by_role("button").first
