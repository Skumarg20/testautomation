"""Settings of the open purchase bill (cog `#aControlRoomSetting`), held for a test and put back.

Fields are drop-downs with fixed ids in purchaseBill.setting.html (`txtModeOfPaymentPurchase`, :196)
and, behind the
"Expiry & MFG" Configure button (`#ExpiryMFG`, :344, window txn-expiry-setting.html), `isExpiaryDate`
("Expiry Date Required?"). Which tab holds each one is unverified live, so the Advance tab is tried when the
field is not on the first tab.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

FIELD_MS = 3_000
TIMEOUT_MS = 15_000
MODE_OF_PAYMENT = "txtModeOfPaymentPurchase"
EXPIRY_REQUIRED = "isExpiaryDate"
EXPIRY_BUTTON = "#ExpiryMFG"


class PurchaseBillSettings(BasePage):
    def current(self, select_id: str) -> str:
        select = self._open(select_id)
        text = select.locator("option:checked").inner_text().strip()
        self._close()
        return text

    def choose(self, select_id: str, wanted: str) -> None:
        select = self._open(select_id)
        select.select_option(label=wanted)
        self._close()

    @contextmanager
    def held(self, select_id: str, wanted: str) -> Iterator[None]:
        original = self.current(select_id)
        if original.lower() == wanted.lower():
            yield
            return
        try:
            self.choose(select_id, wanted)
            yield
        finally:
            self.choose(select_id, original)

    def _open(self, select_id: str) -> Locator:
        self.page.locator("#aControlRoomSetting").locator("visible=true").first.click()
        select = self.page.locator(f"#{select_id}").locator("visible=true").first
        if select_id == EXPIRY_REQUIRED:
            self.page.locator(EXPIRY_BUTTON).locator("visible=true").first.click()
        elif not appears_within(select, FIELD_MS):
            self.page.get_by_text("Advance Setting", exact=True).click()
        select = self.page.locator(f"#{select_id}").locator("visible=true").first
        expect(select).to_be_visible(timeout=TIMEOUT_MS)
        return select

    def _close(self) -> None:
        # Why CSS: the windows' titles are `h2.headingItem` / `.modal-header` with a bare close button.
        self.page.keyboard.press("Escape")
        if appears_within(self.page.locator("h2.headingItem button.close"), FIELD_MS):
            self.page.locator("h2.headingItem button.close").first.click()
