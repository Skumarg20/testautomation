"""Ledgers a test creates for itself, deleted again when the test ends (newest first)."""

from functools import partial

from pages.accounting.opening_balance_page import LedgerSpec, OpeningBalancePage
from pages.components.undo import undo_all


class OwnedLedgers:
    def __init__(self, opening_balances: OpeningBalancePage) -> None:
        self._opening_balances = opening_balances
        self._names: list[str] = []

    def create(self, ledger: LedgerSpec) -> None:
        self._opening_balances.create_ledger(ledger)
        self._names.append(ledger.name)

    def delete_all(self) -> None:
        names = list(reversed(self._names))
        self._names.clear()
        undo_all((name, partial(self._opening_balances.delete_ledger, name)) for name in names)
