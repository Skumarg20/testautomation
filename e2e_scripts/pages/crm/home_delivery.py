"""Home Delivery (/homedelivery): sale bills to deliver, by delivery status (specs/crm-module.md, N2)."""

from typing import Literal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

DeliveryStatus = Literal["Pending", "Delivered", "Counter Delivery", "All"]
# Opened by URL: neither company of the QA login shows Home Delivery under CRM (spec N2).
HOME_DELIVERY_PATH = "/homedelivery"
SCREEN_TIMEOUT_MS = 60_000


class HomeDelivery(BasePage):
    def open(self) -> None:
        self.goto(HOME_DELIVERY_PATH, SCREEN_TIMEOUT_MS)
        expect(self._heading).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def show(self, status: DeliveryStatus) -> None:
        self._status(status).check()

    def expect_showing(self, status: DeliveryStatus) -> None:
        expect(self._status(status)).to_be_checked()

    def expect_columns(self, columns: tuple[str, ...]) -> None:
        for column in columns:
            expect(self.page.get_by_role("columnheader", name=column, exact=True)).to_be_visible()

    def expect_assign_to_offered(self) -> None:
        expect(self.page.get_by_role("button", name="Assign To/Alt+Y")).to_be_visible()

    @property
    def _heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Home Delivery", level=1)

    def _status(self, status: DeliveryStatus) -> Locator:
        return self.page.get_by_role("radio", name=status, exact=True)
