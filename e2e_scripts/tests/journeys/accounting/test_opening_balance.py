"""J18 opening balance entry (specs/opening-balance-entry.md). Each test owns its ledgers and deletes them."""

from decimal import Decimal

import pytest

from pages.accounting.opening_balance_page import LedgerSpec, OpeningBalance, OpeningBalancePage
from pages.accounting.owned_ledgers import OwnedLedgers
from test_data.factory import DataFactory

pytestmark = [pytest.mark.p1, pytest.mark.journey("opening-balance-entry")]


def test_debit_opening_balance_is_listed_on_the_debit_side(
    data: DataFactory, owned_ledgers: OwnedLedgers, opening_balances: OpeningBalancePage
) -> None:
    opening = OpeningBalance(Decimal("1234.50"), "Dr")
    ledger = LedgerSpec(data.party_name("OB-Dr"), opening)

    owned_ledgers.create(ledger)

    assert opening_balances.listed_opening(ledger.name) == opening


def test_credit_opening_balance_is_listed_on_the_credit_side(
    data: DataFactory, owned_ledgers: OwnedLedgers, opening_balances: OpeningBalancePage
) -> None:
    opening = OpeningBalance(Decimal("750.25"), "Cr")
    ledger = LedgerSpec(data.party_name("OB-Cr"), opening)

    owned_ledgers.create(ledger)

    assert opening_balances.listed_opening(ledger.name) == opening


def test_changed_opening_balance_replaces_the_old_one(
    data: DataFactory, owned_ledgers: OwnedLedgers, opening_balances: OpeningBalancePage
) -> None:
    ledger = LedgerSpec(data.party_name("OB-Change"), OpeningBalance(Decimal("1000"), "Dr"))
    owned_ledgers.create(ledger)
    changed = OpeningBalance(Decimal("400"), "Cr")

    opening_balances.change_opening(ledger.name, changed)

    assert opening_balances.listed_opening(ledger.name) == changed
    assert opening_balances.saved_opening(ledger.name) == changed


def test_bill_by_bill_party_keeps_its_opening_balance(
    data: DataFactory, owned_ledgers: OwnedLedgers, opening_balances: OpeningBalancePage
) -> None:
    opening = OpeningBalance(Decimal("1500"), "Dr")
    ledger = LedgerSpec(data.party_name("OB-Bill"), opening, balancing_method="Bill By Bill")

    owned_ledgers.create(ledger)

    assert opening_balances.listed_opening(ledger.name) == opening
