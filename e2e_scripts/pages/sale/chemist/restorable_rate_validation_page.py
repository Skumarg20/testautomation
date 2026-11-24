"""Rate validation that puts the tenant's Default Billing Rate back, since every later sale bill uses it."""

from playwright.sync_api import Locator, Page

from pages.sale.chemist.rate_validation_page import RateValidationPage


class RestorableRateValidationPage(RateValidationPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._original_default_rate: str | None = None

    def set_default_billing_rate(self, rate_letter: str) -> None:
        """Remembers the rate shown before the first change, so it can be put back later."""
        if self._original_default_rate is None:
            self._original_default_rate = self._shown_default_rate()
        super().set_default_billing_rate(rate_letter)

    def restore_default_billing_rate(self) -> None:
        if self._original_default_rate is None:
            return
        self._default_rate_dropdown().select_option(label=self._original_default_rate)
        self._close_sale_bill_setting()

    def _shown_default_rate(self) -> str:
        # Why CSS: a select exposes its chosen option only through the :checked state.
        label = self._default_rate_dropdown().locator("option:checked").inner_text().strip()
        self._close_sale_bill_setting()
        return label

    def _default_rate_dropdown(self) -> Locator:
        self.page.locator("#aControlRoomSetting").click()
        self.page.locator("tabs ul li").last.click()
        self._setting_search.click()
        self._setting_search.press_sequentially("Default Billing Rate")
        return self.page.locator("#DefaultBillingRate")

    def _close_sale_bill_setting(self) -> None:
        title = self.page.locator("h2.headingItem", has_text="Sale Bill Setting")
        title.locator("button.close").click()
