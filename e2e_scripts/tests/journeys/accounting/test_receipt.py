"""Receipt vouchers, ported from the TypeScript suite's accounting.spec.ts."""

import pytest

from pages.accounting.receipt_page import ReceiptPage
from pages.accounting.voucher_cases import load_cases, single_sided_case
from pages.accounting.voucher_flows import SingleSidedFlow
from test_data.document_cases import DocumentCase, case_id

# Voucher number and ledger balances are tenant-wide shared state, so these tests run on one worker.
pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("payments-ledger"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.mark.parametrize("case", load_cases("receipt"), ids=case_id)
def test_receipt_voucher(receipt: ReceiptPage, case: DocumentCase) -> None:
    SingleSidedFlow(receipt, single_sided_case(case, "delete_receipt")).run()
