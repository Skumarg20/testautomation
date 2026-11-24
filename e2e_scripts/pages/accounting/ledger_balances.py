"""Ledger balances read from the ledger master list. Debit balances are positive, credit negative."""

import re
from decimal import Decimal
from typing import NamedTuple

from playwright.sync_api import Locator, expect

from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.list_screen import ListScreen
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage

AMOUNT_DIGITS = re.compile(r"\d+\.?\d*")
CREDIT_MARKER = "cr"
CELL_TIMEOUT_MS = 15_000
REFRESH_TOAST_TIMEOUT_MS = 15_000


class LedgerPair(NamedTuple):
    debit_side: Decimal
    credit_side: Decimal


def signed_balance(text: str) -> Decimal:
    """Reads "5,000.00 Dr" as 5000 and "250.50 Cr" as -250.50; no digits means zero."""
    found = AMOUNT_DIGITS.search(text.replace(",", ""))
    amount = Decimal(found.group()) if found else Decimal(0)
    return -amount if CREDIT_MARKER in text.lower() else amount


class LedgerBalances(BasePage):
    def balance_of(self, name: str) -> Decimal:
        """Refreshes the ledger first, because the list shows a cached balance until then."""
        AccountingMenu(self.page).open_ledger_list()
        return self._refreshed(name)

    def refreshed_pair(self, debit_side_name: str, credit_side_name: str) -> LedgerPair:
        """Refreshes each ledger first, because the list shows a cached balance until then."""
        AccountingMenu(self.page).open_ledger_list()
        return LedgerPair(self._refreshed(debit_side_name), self._refreshed(credit_side_name))

    def expect_balance(self, name: str, expected: Decimal) -> None:
        actual = self.balance_of(name)
        assert actual == expected, f'Ledger balance of "{name}": expected {expected}, found {actual}'

    def expect_pair(self, names: tuple[str, str], expected: LedgerPair) -> None:
        actual = self.refreshed_pair(*names)
        assert actual == expected, f"Ledger balances of {names}: expected {expected}, found {actual}"

    def _refreshed(self, name: str) -> Decimal:
        ListScreen(self.page).search(name)
        self._balance_cell(name).click()
        self.page.get_by_title("Single Ledger Refresh").click()
        Toasts(self.page).expect_success(REFRESH_TOAST_TIMEOUT_MS)
        return self._read(name)

    def _read(self, name: str) -> Decimal:
        cell = self._balance_cell(name)
        expect(cell).to_be_visible(timeout=CELL_TIMEOUT_MS)
        return signed_balance(cell.inner_text())

    def _balance_cell(self, name: str) -> Locator:
        row = self.page.get_by_role("row").filter(has=self.page.get_by_text(name, exact=True))
        # Why CSS: the balance is the grid column with col-id "0"; the header has no usable name.
        return row.locator('[col-id="0"]').first
