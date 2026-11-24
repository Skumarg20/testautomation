"""Contra vouchers, ported from the TypeScript suite's accounting.spec.ts."""

import pytest

from pages.accounting.contra_page import ContraPage
from pages.accounting.voucher_cases import load_cases, two_sided_case
from pages.accounting.voucher_flows import TwoSidedFlow
from test_data.document_cases import DocumentCase, case_id

# Voucher number and ledger balances are tenant-wide shared state, so these tests run on one worker.
pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("payments-ledger"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.mark.parametrize("case", load_cases("contra"), ids=case_id)
def test_contra_voucher(contra: ContraPage, case: DocumentCase) -> None:
    TwoSidedFlow(contra, two_sided_case(case, "credit", "delete_credit_note")).run()
