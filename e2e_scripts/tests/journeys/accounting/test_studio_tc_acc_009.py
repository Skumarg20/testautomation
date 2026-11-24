"""Cash Transfer & Day Closure – CT-09: Zero amount is refused.

Scenario: scenarios/cash-transfer-day-closure.md CT-09. Test case: TC_ACC_009.
Written by Test Studio AI.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.accounting.contra_page import ContraPage
from pages.accounting.opening_balance_page import OpeningBalancePage
from pages.accounting.owned_ledgers import OwnedLedgers
from pages.accounting.opening_balance_page import OpeningBalance
from test_data.banking import LedgerSpec
from test_data.factory import DataFactory
from decimal import Decimal

pytestmark = [pytest.mark.p2, pytest.mark.journey("payments-ledger")]

_ZERO = Decimal(0)


def test_zero_amount_is_refused(
    data: DataFactory,
    owned_ledgers: OwnedLedgers,
    contra: ContraPage,
) -> None:
    """CT-09: saving a contra voucher where both legs are zero is refused."""
    # Arrange – create two fresh ledgers so their balances start at zero
    no_opening = OpeningBalance(_ZERO, "Dr")
    cash_ledger = LedgerSpec(
        name=data.party_name("CashContra"),
        opening=no_opening,
        group="Cash-in-Hand",
    )
    bank_ledger = LedgerSpec(
        name=data.party_name("BankContra"),
        opening=no_opening,
        group="Bank Accounts",
        station="Others",
        account_number="000000",
    )
    owned_ledgers.create(cash_ledger)
    owned_ledgers.create(bank_ledger)

    # Act – open a new contra voucher and enter both legs with amount 0
    contra.open_new_voucher()

    # Row 0: Cr side, cash ledger, credit = 0
    contra.choose_side(0, "credit")
    contra.select_account(0, cash_ledger.name)
    from pages.accounting.voucher_cases import Leg
    contra.enter_leg_amount(0, Leg("credit", cash_ledger.name, "0"))

    # Row 1: Dr side, bank ledger, debit = 0
    contra.choose_side(1, "debit")
    contra.select_account(1, bank_ledger.name)
    contra.enter_leg_amount(1, Leg("debit", bank_ledger.name, "0"))

    # Fill Inst. No. (required for bank leg) and dismiss cheque-book prompt
    page: Page = contra.page
    page.get_by_label("Inst. No").fill("123456")
    page.get_by_label("Inst. No").press("Enter")
    # Dismiss "Do you want to create cheque book?" dialog if it appears
    cheque_dialog = page.get_by_role("button", name="No")
    if cheque_dialog.is_visible():
        cheque_dialog.click()

    # Try to save
    contra.save()

    # Assert – the form must be rejected (stays open, warning shown)
    contra.expect_rejected()
