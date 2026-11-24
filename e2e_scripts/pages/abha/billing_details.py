"""The "Select Billing for Abha Number" popup the sale bill's "Select ABHA Address" option opens
(`abha-selection-details.component.html/.ts`): the patient's ABHA rows from `GetPatientAbhaDetails`; a click
on a row links that ABHA to the bill (`.ts:36-39`, `processout.transaction.component.ts:19767-19778`).
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

TITLE = "Select Billing for Abha Number"
POPUP_TIMEOUT_MS = 15_000
ACTIVE = "Active"


class AbhaBillingDetails(BasePage):
    def expect_shown(self) -> None:
        expect(self._popup).to_be_visible(timeout=POPUP_TIMEOUT_MS)

    def expect_row(self, abha_number: str, abha_address: str) -> None:
        row = self._row(abha_number)
        expect(row.get_by_role("cell", name=abha_address, exact=True)).to_be_visible()
        expect(row.get_by_role("cell", name=ACTIVE, exact=True)).to_be_visible()

    def choose(self, abha_number: str) -> None:
        self._row(abha_number).click()
        expect(self._popup).to_be_hidden(timeout=POPUP_TIMEOUT_MS)

    def _row(self, abha_number: str) -> Locator:
        return self._popup.get_by_role("row").filter(
            has=self.page.get_by_role("cell", name=abha_number, exact=True)
        )

    @property
    def _popup(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has=self.page.get_by_role("heading", name=TITLE))
