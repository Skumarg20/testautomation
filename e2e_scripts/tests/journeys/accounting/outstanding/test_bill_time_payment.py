"""OA-041 to OA-060 and OA-100: payment taken in the sale bill's Mode Of Payment window when it is saved.

The window opens on save while the Sale Bill Setting "Mode of Payment Required ?" is Yes, as it was on the
garments company on 2026-10-09; with it off, every bill would be saved without the window.
Workbook: TestCase_Outstanding.xlsx; scenario pack: scenarios/outstanding-advance.md.
"""

import pytest

from pages.accounting.outstanding.scenario import OutstandingScenario
from test_data.outstanding_cases import BILL_TIME_PAYMENT
from test_data.outstanding_params import as_params
from test_data.outstanding_steps import OutstandingCase

pytestmark = [pytest.mark.p1, pytest.mark.journey("payments-ledger")]


@pytest.mark.parametrize("case", as_params(BILL_TIME_PAYMENT))
def test_party_outstanding_and_advance(scenario: OutstandingScenario, case: OutstandingCase) -> None:
    scenario.play(case)
    scenario.expect_balances(case.expected)
