"""Test data for the bank and ledger-report journeys (J11, J12): own ledgers and bank vouchers."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from test_data.factory import DataFactory

BANK_GROUP = "Bank Accounts"
EXPENSE_GROUP = "Indirect Expenses"
BANK_STATION = "Others"
BANK_ACCOUNT_NUMBER = "1234567890"
PAYMENT_AMOUNT = Decimal("1000.50")
RECEIPT_AMOUNT = Decimal("400.25")
PAYMENT_CHEQUE = "100001"
RECEIPT_CHEQUE = "200002"


class VoucherKind(str, Enum):
    """The voucher types as the app names them in lists, the reconciliation grid and the ledger report."""

    PAYMENT = "Payment"
    RECEIPT = "Receipt"


@dataclass(frozen=True)
class LedgerSpec:
    """A ledger the test creates. Bank ledgers need a station and an account number; expenses do not."""

    name: str
    group: str
    station: str | None = None
    account_number: str | None = None


@dataclass(frozen=True)
class BankEntry:
    """A receipt or payment made through a bank ledger by cheque, against one account."""

    kind: VoucherKind
    account: str
    amount: Decimal
    cheque_number: str

    @property
    def typed_amount(self) -> str:
        return f"{self.amount:.2f}"


@dataclass(frozen=True)
class SavedVoucher:
    """A saved bank voucher. The account is kept because the number alone may not be unique (BK-10)."""

    kind: VoucherKind
    number: str
    account: str
    day: date


@dataclass(frozen=True)
class BankLedgers:
    bank: LedgerSpec
    expense: LedgerSpec

    def payment(self) -> BankEntry:
        return BankEntry(VoucherKind.PAYMENT, self.expense.name, PAYMENT_AMOUNT, PAYMENT_CHEQUE)

    def receipt(self) -> BankEntry:
        return BankEntry(VoucherKind.RECEIPT, self.expense.name, RECEIPT_AMOUNT, RECEIPT_CHEQUE)


def bank_ledgers(data: DataFactory) -> BankLedgers:
    """A new bank ledger and a new expense ledger, so no other test moves their balances."""
    bank = LedgerSpec(data.party_name("Bank"), BANK_GROUP, BANK_STATION, BANK_ACCOUNT_NUMBER)
    return BankLedgers(bank, LedgerSpec(data.party_name("Exp"), EXPENSE_GROUP))
