"""The totals of an open bill screen (sale or purchase): tax ledger rows and the invoice value."""

import re
from contextlib import suppress
from decimal import Decimal

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from pages.grid.ag_grid import AgGrid
from test_data.money import parse_amount

TAX_LEDGER = "ledgerLinkID"
TAX_AMOUNT = "amount"
INVOICE_VALUE = re.compile(r"Invoice Value\s*:\s*₹?\s*(-?[\d.,]+)")
CALCULATION_TIMEOUT_MS = 15_000
DISCARD_PROMPT_TIMEOUT_MS = 4_000
CLOSE_TIMEOUT_MS = 10_000
MAX_DIALOG_LAYERS = 3
DIALOG_CLOSE_TIMEOUT_MS = 2_000
THREE_PLACES = Decimal("0.001")


class BillTotals(BasePage):
    def invoice_value(self) -> Decimal:
        shown = INVOICE_VALUE.search(self._invoice_value_panel.inner_text())
        if shown is None:
            raise LookupError("The bill screen shows no 'Invoice Value' amount")
        return parse_amount(shown.group(1))

    def expect_invoice_value(self, expected: Decimal) -> None:
        """Waits until the screen has finished calculating and shows `expected` (3 decimals)."""
        expect(self._invoice_value_panel).to_have_text(
            re.compile(rf"Invoice Value\s*:\s*₹?\s*{amount_pattern(expected)}\s*$"),
            timeout=CALCULATION_TIMEOUT_MS,
        )

    def tax_amounts(self) -> dict[str, Decimal]:
        """Tax ledger rows with an amount, for example {"CGST Output": 7.5, "SGST Output": 7.5}."""
        rows = AgGrid(self.page, TAX_LEDGER).body.locator(".ag-row")
        taxes = {}
        for index in range(rows.count()):
            ledger, amount = self._ledger_and_amount(rows.nth(index))
            if amount:
                taxes[ledger] = parse_amount(amount)
        return taxes

    def leave_without_saving(self) -> None:
        """Closes the bill; a dialog still open over it (an alert, a picker) is dismissed first."""
        self._dismiss_open_dialogs()
        self.page.locator("[id^=btnEsc]").click(timeout=CLOSE_TIMEOUT_MS)
        yes_button = self.page.locator("#btnYes")
        try:
            yes_button.wait_for(state="visible", timeout=DISCARD_PROMPT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            return  # An untouched bill closes without asking.
        yes_button.click()

    def _dismiss_open_dialogs(self) -> None:
        # Angular leaves closed dialogs in the DOM with aria-hidden set; only the others are open.
        dialogs = self.page.locator("ngb-modal-window:not([aria-hidden='true'])")
        for _ in range(MAX_DIALOG_LAYERS):
            open_dialogs = dialogs.count()
            if open_dialogs == 0:
                return
            self.page.keyboard.press("Escape")
            # A dialog that ignores Escape is left to the next round, which presses Escape again.
            with suppress(AssertionError):
                expect(dialogs).to_have_count(open_dialogs - 1, timeout=DIALOG_CLOSE_TIMEOUT_MS)

    def expect_tax_amounts(self, expected: dict[str, Decimal]) -> None:
        """Waits until the tax ledger rows are exactly `expected` (3 decimals)."""
        rows = AgGrid(self.page, TAX_LEDGER).body.locator(".ag-row").filter(has_text=re.compile(r"\d"))
        patterns = [
            re.compile(rf"^{ledger}\s*{amount_pattern(amount)}$") for ledger, amount in expected.items()
        ]
        expect(rows).to_have_text(patterns, timeout=CALCULATION_TIMEOUT_MS)

    @property
    def _invoice_value_panel(self) -> Locator:
        return self.page.locator("div").filter(has_text=INVOICE_VALUE).last

    @staticmethod
    def _ledger_and_amount(row: Locator) -> tuple[str, str]:
        ledger = row.locator(f'[col-id="{TAX_LEDGER}"]').inner_text().strip()
        amount = row.locator(f'[col-id="{TAX_AMOUNT}"]').inner_text().strip()
        return ledger, amount


def amount_pattern(amount: Decimal) -> str:
    """Regex for how the app shows `amount`: 3 decimals, optional thousands separators."""
    whole, fraction = f"{amount.quantize(THREE_PLACES)}".split(".")
    grouped_whole = ",?".join(whole.lstrip("-"))
    return f"{'-' if amount < 0 else ''}{grouped_whole}\\.{fraction}"
