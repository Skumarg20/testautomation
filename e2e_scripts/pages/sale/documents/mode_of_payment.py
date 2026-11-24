"""The Mode Of Payment window a sale bill opens on save: the amount taken now (bill-time payment).

The first row is Cash Account; its amount editor `#txt-amount-0` has focus when the window opens. Leaving it
at zero saves a credit bill. More than the bill amount is refused with "Please Enter less then Bill amount"
(global.ts:19350, modeofpayment.component.ts:527). Seen live 2026-10-09.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

TITLE = "Mode Of Payment"
CASH_AMOUNT = "#txt-amount-0"
SAVE_BUTTON = "#btn-Save"
ABOVE_BILL_AMOUNT = re.compile(r"Please Enter less then Bill amount", re.IGNORECASE)
WINDOW_TIMEOUT_MS = 30_000
REFUSAL_LOOKUP_MS = 3_000


class PaymentRefusedError(AssertionError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Mode Of Payment refused to save: {message}")


class ModeOfPayment(BasePage):
    def is_open(self, timeout_ms: int) -> bool:
        return appears_within(self._window, timeout_ms)

    def expect_open(self) -> None:
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def take_cash(self, amount: Decimal) -> None:
        # The window holds two #txt-amount-0 inputs (OA-041, 2026-10-13); the first has focus on open.
        editor = self._window.locator(CASH_AMOUNT).first
        if not editor.is_visible():
            self._window.locator('[row-id="0"] [col-id="amount"]').dblclick()
        editor.press("Control+A")
        editor.press_sequentially(format(amount, "f"))
        editor.press("Enter")

    def save(self) -> None:
        """Saves; a refusal (e.g. "Please Check Total Amount" when the bill drops below what was already
        received, OA-004 on 2026-10-09) fails with the app's own message."""
        # Why an id: the window has a hidden second Save button with the same name.
        self._window.locator(SAVE_BUTTON).click()
        warning = self.page.locator("notifier-notification.notifier__notification--warning").first
        if appears_within(warning, REFUSAL_LOOKUP_MS) and self._window.is_visible():
            raise PaymentRefusedError(warning.inner_text().strip())
        expect(self._window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    def expect_above_bill_amount_refused(self) -> None:
        expect(self.page.get_by_text(ABOVE_BILL_AMOUNT).first).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    @property
    def _window(self) -> Locator:
        return self.page.locator("ngb-modal-window").filter(has_text=TITLE)
