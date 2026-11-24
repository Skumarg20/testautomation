"""The "Credit Limit Alert!" window of a sale bill.

Source: Component/Transaction/InverntoryTransaction/childcomponents/primaryorcreditlimit.template.ts. It lists
"Party Limit", "Party Balance" and "Difference" (the bill total minus what the limit still allows) and ends in
Yes / No for "Only Indicate" (title Confirmation) or OK for "Follow Strictly". The decision is made in
processout.transaction.component.ts:13621-13665 (`checkCreditLimits`): available = limit minus the party's
debit balance; when it is below the bill total the window opens. "Stop Billing" (case 3) is an empty branch on
the web (:13650), so no window is drawn for it.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

ALERT_TIMEOUT_MS = 30_000
HEADING = re.compile(r"Credit Limit Alert", re.IGNORECASE)


class CreditLimitAlert(BasePage):
    def expect_shown(self) -> None:
        expect(self._window).to_be_visible(timeout=ALERT_TIMEOUT_MS)

    def expect_not_shown(self) -> None:
        expect(self._window).to_have_count(0)

    def expect_difference(self, amount: Decimal) -> None:
        """The "Difference -" row shows the amount with two decimals (`number : '1.2-2'`)."""
        row = self._window.locator(".row").filter(has_text="Difference")
        expect(row).to_contain_text(f"{amount:,.2f}", timeout=ALERT_TIMEOUT_MS)

    def expect_party_limit(self, amount: Decimal) -> None:
        row = self._window.locator(".row").filter(has_text="Party Limit")
        expect(row).to_contain_text(f"{amount:,.2f}", timeout=ALERT_TIMEOUT_MS)

    def expect_choice(self, buttons: tuple[str, ...]) -> None:
        for name in buttons:
            expect(
                self._window.get_by_role("button", name=re.compile(name, re.IGNORECASE)).first
            ).to_be_visible()

    def answer(self, button: str) -> None:
        self._window.get_by_role("button", name=re.compile(button, re.IGNORECASE)).first.click()
        expect(self._window).to_be_hidden(timeout=ALERT_TIMEOUT_MS)

    @property
    def _window(self) -> Locator:
        return self.page.locator("ngb-modal-window").filter(has_text=HEADING)
