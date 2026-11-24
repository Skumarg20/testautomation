"""Sale bill row 49: a negative quantity.

Rule: the quantity editor's mask 'Ndecimal' lets "-" through (input-mask-directive.ts:20-30, global.ts:19866);
the cell check only refuses 0 (processout.transaction.component.ts:7345); only a service item refuses a
negative
(global.ts:19415). Without the Control Room right 4419 (negative quantity, :1366) a save with a negative
invoice
stops with "Bill amount greater than or equal to 0" (:10842, global.ts:19382) and nothing is saved.
DECISION NEEDED: the sheet says "warning at once"; the code warns at save.
"""

from decimal import Decimal

import pytest

from pages.accounting.outstanding.document_list import DocumentList
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.manual.pharma_bill import PARTY, PharmaBill

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

BILL_AMOUNT_NEGATIVE = "Bill amount greater than or equal to 0"


def test_negative_quantity_cannot_be_saved(bill: PharmaBill) -> None:
    before = DocumentList(bill.page, SaleBillDocument.menu).numbers_for(PARTY)
    bill.start()
    bill.pick_item(0, Decimal(1))
    bill.type_quantity(0, "-2")

    bill.try_save()

    bill.messages.expect_warning(BILL_AMOUNT_NEGATIVE)
    bill.leave_without_saving()
    assert DocumentList(bill.page, SaleBillDocument.menu).numbers_for(PARTY) == before
