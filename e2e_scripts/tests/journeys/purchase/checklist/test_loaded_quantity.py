"""Purchase checklist rows 10 and 11: the quantity of a line that a bill took over from a challan.

Rule cited: a line loaded from a purchase challan cannot go above the challan's quantity; the app puts the
challan's quantity back and warns "Quantity should be less than or equals to Purchase Challan Quantity i.e.
<n>!" (transactionin.component.ts:6603-6620, `AlertMsg.ValidQty` Globals/global.ts:19315). A lower quantity
passes that check. The same check for lines loaded from an order (`itemLoadedFrom` 3, :14693) is not found in
the source, so the order half of rows 10 and 11 is left open.
"""

from decimal import Decimal

import pytest

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.feedback import ToastKind

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

CHALLAN_QUANTITY = Decimal(100)
ABOVE_CHALLAN = Decimal(101)
BELOW_CHALLAN = Decimal(40)
NO_WARNING_WAIT_MS = 2_500
OVER_CHALLAN_MESSAGE = "Quantity should be less than or equals to Purchase Challan Quantity i.e."


def test_quantity_above_the_challans_is_refused_and_put_back(
    bill_from_challan: PurchaseBillEntryPage,
) -> None:
    bill_from_challan.grid.type_quantity(0, ABOVE_CHALLAN)

    bill_from_challan.feedback.expect_toast_saying(ToastKind.WARNING, OVER_CHALLAN_MESSAGE)
    assert bill_from_challan.grid.product(0).quantity == CHALLAN_QUANTITY


def test_quantity_below_the_challans_is_accepted(bill_from_challan: PurchaseBillEntryPage) -> None:
    bill_from_challan.grid.type_quantity(0, BELOW_CHALLAN)

    assert not bill_from_challan.feedback.toast_appears(ToastKind.WARNING, NO_WARNING_WAIT_MS)
    assert bill_from_challan.grid.product(0).quantity == BELOW_CHALLAN
