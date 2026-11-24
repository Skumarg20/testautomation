"""Sale bill row 145: the focus follows Enter through a line.

Cells have the editor id "txt-<col-id>-<row>" (template.sale.decimalformat.ts:42). After the item and
batch are
chosen the quantity editor holds the cursor; after the quantity and Enter the rate editor does
(`enableSelectedGridCellForEdit(rowIndex, "salePurchaseRate")`, processout.transaction.component.ts:12767;
setting onwhichfieldCursorshouldwait). Unverified live; the order is the app's own, not the sheet's.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.sale.manual.pharma_bill import PharmaBill

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

FOCUS_MS = 10_000


def test_cursor_goes_batch_then_quantity_then_rate(bill: PharmaBill) -> None:
    bill.start()
    bill.document.grid.select_product(0, "44646015")
    bill.document.grid.choose_batch(0, "1231231123")
    expect(bill.page.locator("#txt-unitToEnteredValue-0")).to_be_focused(timeout=FOCUS_MS)

    bill.document.grid.enter_quantity(0, Decimal(1))

    expect(bill.page.locator("#txt-salePurchaseRate-0")).to_be_focused(timeout=FOCUS_MS)
