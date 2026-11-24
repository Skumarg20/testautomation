"""Debit note vouchers, ported from the TypeScript suite's accounting.spec.ts."""

import pytest

from pages.accounting.debit_note_page import DebitNotePage
from pages.accounting.voucher_cases import load_cases, two_sided_case
from pages.accounting.voucher_flows import TwoSidedFlow
from test_data.document_cases import DocumentCase, case_id

# Voucher number and ledger balances are tenant-wide shared state, so these tests run on one worker.
pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("payments-ledger"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.mark.parametrize("case", load_cases("debit-note"), ids=case_id)
def test_debit_note_voucher(debit_note: DebitNotePage, case: DocumentCase) -> None:
    TwoSidedFlow(debit_note, two_sided_case(case, "debit", "delete_debit_note")).run()
