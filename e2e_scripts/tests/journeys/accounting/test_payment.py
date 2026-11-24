"""Payment vouchers, ported from the TypeScript suite's accounting.spec.ts."""

import pytest

from pages.accounting.payment_page import PaymentPage
from pages.accounting.voucher_cases import load_cases, single_sided_case
from pages.accounting.voucher_flows import SingleSidedFlow
from test_data.document_cases import DocumentCase, case_id

# Voucher number and ledger balances are tenant-wide shared state, so these tests run on one worker.
pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("payments-ledger"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.mark.parametrize("case", load_cases("payment"), ids=case_id)
def test_payment_voucher(payment: PaymentPage, case: DocumentCase) -> None:
    SingleSidedFlow(payment, single_sided_case(case, "delete_payment")).run()
