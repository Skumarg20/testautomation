"""The cash and bank ledgers and the deposits one test owns, and how to undo them after the test."""

from decimal import Decimal
from functools import partial

from playwright.sync_api import Page

from pages.accounting.ledger_balances import LedgerPair
from pages.banking.ledger_setup import LedgerSetup
from pages.cash_transfer.contra_transfer import ContraTransfer
from pages.cash_transfer.ledger_closing_balance import LedgerClosingBalance
from pages.components.undo import UndoStep, undo_all
from test_data.cash_transfer import CashBankLedgers, CashDeposit


class CashTransferBook:
    """The app refuses to delete a ledger that has vouchers, so undo deletes the deposits first."""

    def __init__(self, page: Page, ledgers: CashBankLedgers) -> None:
        self.page = page
        self.ledgers = ledgers
        self.contra = ContraTransfer(page)
        self._deposits: list[CashDeposit] = []
        self._created_ledgers: list[str] = []

    def open(self) -> None:
        setup = LedgerSetup(self.page)
        for ledger in (self.ledgers.cash, self.ledgers.bank):
            setup.create(ledger)
            self._created_ledgers.append(ledger.name)

    def deposit(self) -> CashDeposit:
        """Saves today's deposit of the default amount and remembers it for the undo."""
        deposit = self.ledgers.deposit()
        self.contra.record(deposit)
        self._deposits.append(deposit)
        return deposit

    def change_amount(self, deposit: CashDeposit, amount: Decimal) -> CashDeposit:
        self.contra.change_amount(deposit, amount)
        changed = deposit.with_amount(amount)
        self._deposits[self._deposits.index(deposit)] = changed
        return changed

    def delete(self, deposit: CashDeposit) -> None:
        self.contra.delete(deposit)
        self._deposits.remove(deposit)

    def balances(self) -> LedgerPair:
        """Closing balances from each ledger's own report: debit side the bank, credit side the cash."""
        return LedgerPair(
            self._closing_balance(self.ledgers.bank.name), self._closing_balance(self.ledgers.cash.name)
        )

    def _closing_balance(self, ledger: str) -> Decimal:
        return LedgerClosingBalance(self.page).of(ledger)

    def close(self) -> None:
        undos = [*self._deposit_undos(), *self._ledger_undos()]
        self._deposits.clear()
        undo_all(undos)

    def _deposit_undos(self) -> list[UndoStep]:
        return [
            (f"deposit from {deposit.cash_ledger}", partial(self.contra.delete, deposit))
            for deposit in reversed(self._deposits)
        ]

    def _ledger_undos(self) -> list[UndoStep]:
        setup = LedgerSetup(self.page)
        return [(f"ledger {name}", partial(setup.delete, name)) for name in reversed(self._created_ledgers)]
