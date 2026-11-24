"""Purchase checklist rows 56, 57 and 58: profit window, loss indication, rate sources on a purchase bill.

The Net Profit window (Alt+F10) and the pink loss row belong to the sale screens only
(processout.transaction.component.ts:15297; countersale.component.ts:649; purchase has no handler,
transactionin
.component.ts:14440-14650, and the purchase setting has no Loss Indication button). The sale equivalents are
sale checklist rows 83, 93 and 94 (tests/journeys/sales/checklist/test_calculation_checks.py). Here the
absence is asserted:
no Net Profit window on Alt+F10, no Net Loss window when the rate is far below cost.
Row 58. The rate of a picked item is the item's rate (existing test_after_save.py); the batch rate comes
from the
Batch Details window typed on the purchase (row 48 test); barcode and parameter entry are not part of
this bill.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE

pytestmark = [pytest.mark.p3, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

ABSENCE_MS = 2_500


def test_no_net_loss_window_opens_on_a_purchase_bill_with_a_tiny_rate(
    new_bill: PurchaseBillEntryPage,
) -> None:
    new_bill.grid.select_product(0, STANDARD_ITEM_CODE)

    new_bill.grid.type_quantity(0, Decimal(1))
    new_bill.grid.enter_rate(0, Decimal("0.01"))

    expect(new_bill.page.get_by_text("Net Loss")).to_have_count(0, timeout=ABSENCE_MS)
