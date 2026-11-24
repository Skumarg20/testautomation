"""The Additional Details grid of a sale bill (`#transactionGridAd<tab>`, columns ledgerLinkID /
percentage / amount).

processout.transaction.component.ts:8139-8180 (columns), componentPlaceHolder.template.ts:155-205 (a click or
Enter on the ledger cell opens the "Select Expense" ledger list, picking a ledger fills the row and moves to
the % cell), dataCalculation.ts:872-880 and :959-971 (a % charge = (goods - bill discount) x % / 100; an
amount
charge is taken as typed). The grid needs a filled item row first (componentPlaceHolder.template.ts:157-160).
"""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.grid.ag_grid import AgGrid
from pages.sale.round2_c1.cells import number_text

LEDGER = "ledgerLinkID"
PERCENTAGE = "percentage"
AMOUNT = "amount"
PICKER_TIMEOUT_MS = 20_000


class AdditionalChargesGrid(BasePage):
    def add_charge(self, ledger: str) -> None:
        """Opens the list from the empty last row (tax rows come first) and picks `ledger`."""
        cell = self._empty_row().locator(f'[col-id="{LEDGER}"]')
        cell.click()
        cell.press("Enter")
        picker = self.page.get_by_role("gridcell", name=ledger, exact=True).first
        expect(picker).to_be_visible(timeout=PICKER_TIMEOUT_MS)
        picker.dblclick()

    def set_percentage(self, ledger: str, percentage: Decimal) -> None:
        self._type(self._cell(ledger, PERCENTAGE), percentage)

    def set_amount(self, ledger: str, amount: Decimal) -> None:
        self._type(self._cell(ledger, AMOUNT), amount)

    def remove_charge(self, ledger: str) -> None:
        row = self._row_of(ledger)
        row.hover()
        row.get_by_title("Delete").click()
        self.page.locator("#btnYes").click()

    def expect_amount(self, ledger: str, expected: Decimal) -> None:
        expect(self._cell(ledger, AMOUNT)).to_have_text(number_text(expected), timeout=PICKER_TIMEOUT_MS)

    def expect_absent(self, ledger: str) -> None:
        expect(self._row_of(ledger)).to_have_count(0, timeout=PICKER_TIMEOUT_MS)

    def _type(self, cell: Locator, value: Decimal) -> None:
        cell.click()
        editor = cell.locator("input")
        editor.press("Control+A")
        editor.press_sequentially(f"{value:f}")
        editor.press("Enter")

    def _empty_row(self) -> Locator:
        return AgGrid(self.page, LEDGER).body.locator(".ag-row").last

    def _row_of(self, ledger: str) -> Locator:
        return AgGrid(self.page, LEDGER).body.locator(".ag-row").filter(has_text=ledger)

    def _cell(self, ledger: str, column: str) -> Locator:
        return self._row_of(ledger).locator(f'[col-id="{column}"]')
