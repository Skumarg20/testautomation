"""The "Batch Details" window a purchase line opens for a new batch (MRP, sale rates A to H, margin table).

Component `TransactionInBatchComponent` (Component/Transaction/InverntoryTransaction/TransactionIn/
transactioninbatch.component.ts, template UI/.../transactioninbatch.component.html). Field ids: `txtmrp`
(:154), `txtratea` (:194), `txtrateb` ... `txtrateh` (:210-308); a refused value shows its text in the
`validation-message` beside the field. Rule texts: transactioninbatch.component.ts:1008-1110 (they apply when
Control Room field 4163's seventh action is "F"). Margin table: :394-400, its last row is the "New" batch.
Locators are from the source and unverified live.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.checklist.line_math import Cost
from pages.purchase.documents.feedback import appears_within
from test_data.money import parse_amount

WINDOW_TIMEOUT_MS = 10_000
MESSAGE_TIMEOUT_MS = 4_000
WITH_DEAL_COLUMN = 1
WITHOUT_DEAL_COLUMN = 3


class BatchDetailsWindow(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._window = page.locator("ngb-modal-window").filter(has_text="Batch Details").last

    def expect_open(self) -> None:
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def has_rate(self, letter: str) -> bool:
        return appears_within(self._rate_field(letter), MESSAGE_TIMEOUT_MS)

    def type_mrp(self, amount: Decimal) -> None:
        self._type(self._window.locator("#txtmrp"), amount)

    def type_rate(self, letter: str, amount: Decimal) -> None:
        self._type(self._rate_field(letter), amount)

    def mrp(self) -> Decimal:
        return parse_amount(self._window.locator("#txtmrp").input_value())

    def says(self, message: str) -> bool:
        """True when the window shows `message` beside a field within a few seconds."""
        return appears_within(self._window.get_by_text(message), MESSAGE_TIMEOUT_MS)

    def new_batch_cost(self) -> Cost:
        row = self._window.locator("tbody tr").filter(has_text=re.compile(r"^\s*New\b")).last
        cells = row.locator("td")
        return Cost(
            parse_amount(cells.nth(WITH_DEAL_COLUMN).inner_text()),
            parse_amount(cells.nth(WITHOUT_DEAL_COLUMN).inner_text()),
        )

    def fill_and_close(self, mrp: Decimal, rate_a: Decimal) -> None:
        """MRP and sale rate A, then Enter closes the window (the seed purchases close it the same way)."""
        self.type_mrp(mrp)
        self.type_rate("a", rate_a)
        self._rate_field("a").press("Enter")

    def close(self) -> None:
        self.page.keyboard.press("Escape")

    def _rate_field(self, letter: str) -> Locator:
        return self._window.locator(f"#txtrate{letter.lower()}")

    @staticmethod
    def _type(field: Locator, amount: Decimal) -> None:
        field.click()
        field.press("Control+A")
        field.press_sequentially(format(amount, "f"))
        field.press("Tab")
