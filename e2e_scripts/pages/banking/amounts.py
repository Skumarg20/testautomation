"""Amounts as the bank and ledger screens print them: "1,000.50", "1000.500", "" (none) or "600.250 Dr"."""

from decimal import Decimal

from pages.accounting.ledger_balances import signed_balance


def amount_in(cell_text: str) -> Decimal:
    """An unsigned amount cell; an empty cell means no amount on that side."""
    digits = cell_text.replace(",", "").strip()
    return Decimal(digits) if digits else Decimal(0)


def balance_in(cell_text: str) -> Decimal:
    """A balance cell with its Dr/Cr marker: debit balances are positive, credit balances negative."""
    return signed_balance(cell_text)
