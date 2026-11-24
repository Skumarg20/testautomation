"""OA-061 to OA-080: advance receipts and their adjustment to later bills.

Workbook: TestCase_Outstanding.xlsx; scenario pack: scenarios/outstanding-advance.md.
"""

import pytest

from pages.accounting.outstanding.scenario import OutstandingScenario
from test_data.outstanding_cases import ADVANCE
from test_data.outstanding_params import as_params
from test_data.outstanding_steps import OutstandingCase

pytestmark = [pytest.mark.p1, pytest.mark.journey("payments-ledger")]


@pytest.mark.parametrize("case", as_params(ADVANCE))
def test_party_outstanding_and_advance(scenario: OutstandingScenario, case: OutstandingCase) -> None:
    scenario.play(case)
    scenario.expect_balances(case.expected)
