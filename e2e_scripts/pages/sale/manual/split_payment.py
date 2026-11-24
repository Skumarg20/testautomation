"""Mode Of Payment with more than one payment ledger, on a garments sale bill saved through `SaleBillDesk`.

The window's grid (`#modeOfPaymentGrid`, modeofpayment.component.ts:392-397) has one row per payment ledger
with an editable Amount column; the first row is Cash Account. A total above the bill is refused with "Please
check total amount" (:589-594, global.ts:19352). Further ledgers come from the window's own settings (Add),
which no test changes, so a split needs a company that already lists a second ledger.
"""

from decimal import Decimal

from playwright.sync_api import Locator, Page

from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.base_page import BasePage

MODE_OF_PAYMENT_GRID = "#modeOfPaymentGrid"


class SecondPaymentLedgerMissingError(Exception):
    """The Mode Of Payment window lists only one ledger, so nothing can be split."""

    def __init__(self) -> None:
        super().__init__("The Mode Of Payment window lists only one payment ledger")


class PaymentRows(BasePage):
    def count(self) -> int:
        return self._grid.locator(".ag-row").count()

    def take(self, row: int, amount: Decimal) -> None:
        """Types the amount taken in the ledger of the 0-based `row`."""
        # Why ids and col-ids: the window's editors are named by column and row (`#txt-amount-<row>`).
        editor = self._grid.locator(f"#txt-amount-{row}").first
        if not editor.is_visible():
            self._grid.locator(f'[row-id="{row}"] [col-id="amount"]').dblclick()
        editor.press("Control+A")
        editor.press_sequentially(format(amount, "f"))
        editor.press("Enter")

    @property
    def _grid(self) -> Locator:
        window = self.page.locator("ngb-modal-window").filter(has_text="Mode Of Payment")
        return window.locator(MODE_OF_PAYMENT_GRID)


class SplitPaymentDesk(SaleBillDesk):
    def __init__(self, page: Page, item: str) -> None:
        super().__init__(page, item)
        self.page = page
        self._rows = PaymentRows(page)

    def create_paid_across_two_ledgers(
        self, party: str, amount: Decimal, split: tuple[Decimal, Decimal]
    ) -> str:
        """Saves a bill of `amount` taking `split[0]` in the first ledger and `split[1]` in the second."""
        self._start(party, amount)
        self._open_payment_window()
        if self._rows.count() < 2:
            raise SecondPaymentLedgerMissingError
        for row, paid in enumerate(split):
            if paid > 0:
                self._rows.take(row, paid)
        self._save_payment()
        return self._saved_number(party)
