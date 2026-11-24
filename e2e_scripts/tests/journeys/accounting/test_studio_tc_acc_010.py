"""Cash Transfer & Day Closure – CT-10: non-cash/bank ledger is not offered / refused in contra.

Scenario: scenarios/cash-transfer-day-closure.md CT-10. Test case: TC_ACC_010.
Written by Test Studio AI.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.accounting.contra_page import ContraPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("payments-ledger")]

_DEBTOR_LEDGER = "QA_Party_Debtor"


def test_a_non_cash_bank_ledger_is_not_offered_refused_in(
    contra: ContraPage,
) -> None:
    """CT-10: the contra account popup must not list non-cash/bank ledgers such as QA_Party_Debtor."""
    # Arrange – open a new contra voucher
    contra.open_new_voucher()

    # Act – click Account on row 0 (Cr side, default) and type the debtor ledger name
    contra.select_account(0, _DEBTOR_LEDGER)

    # Assert 1 – the ledger popup is open
    assert contra.ledgers_window_is_open(), "Ledger popup did not open after clicking Account"

    # Assert 2 – QA_Party_Debtor must NOT appear in the popup list
    ledger_list = contra.ledgers
    expect(
        ledger_list.get_by_text(_DEBTOR_LEDGER, exact=True)
    ).not_to_be_visible(
        message=(
            f"{_DEBTOR_LEDGER} (Sundry Debtors) appeared in the contra account popup; "
            "only Cash-in-Hand and Bank Accounts ledgers should be offered – log as defect."
        )
    )

    # Cleanup – close the popup so the fixture teardown can navigate away cleanly
    contra.close_ledgers_window()
