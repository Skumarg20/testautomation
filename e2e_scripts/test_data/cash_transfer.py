"""Test data for the cash transfer journey (J29): own cash and bank ledgers and the contra between them."""

from dataclasses import dataclass, replace
from decimal import Decimal

from test_data.banking import BANK_ACCOUNT_NUMBER, BANK_GROUP, BANK_STATION, LedgerSpec
from test_data.factory import DataFactory

CASH_GROUP = "Cash-in-Hand"
DEPOSIT_AMOUNT = Decimal("500")
CHANGED_AMOUNT = Decimal("750")
DEPOSIT_CHEQUE = "123456"


@dataclass(frozen=True)
class CashDeposit:
    """Cash paid into the bank: Cr the cash ledger, Dr the bank ledger, the same amount on both rows."""

    cash_ledger: str
    bank_ledger: str
    amount: Decimal
    cheque_number: str = DEPOSIT_CHEQUE

    @property
    def typed_amount(self) -> str:
        return f"{self.amount:.2f}"

    def with_amount(self, amount: Decimal) -> "CashDeposit":
        return replace(self, amount=amount)


@dataclass(frozen=True)
class CashBankLedgers:
    cash: LedgerSpec
    bank: LedgerSpec

    def deposit(self) -> CashDeposit:
        return CashDeposit(self.cash.name, self.bank.name, DEPOSIT_AMOUNT)


def cash_bank_ledgers(data: DataFactory) -> CashBankLedgers:
    """A new cash ledger and bank ledger, so no other test moves their balances."""
    cash = LedgerSpec(data.party_name("Cash"), CASH_GROUP)
    bank = LedgerSpec(data.party_name("Bank"), BANK_GROUP, BANK_STATION, BANK_ACCOUNT_NUMBER)
    return CashBankLedgers(cash, bank)
