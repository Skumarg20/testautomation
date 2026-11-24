"""Purchase checklist rows 9, 10, 11 for a bill that took over a purchase order.

Row 10/11 for an order. The quantity limit "Quantity should be less than or equals to Purchase Challan
Quantity"
is checked in `checkEnteredQtyValid` only for lines whose `oldDataType` is a purchase challan, bill or return
challan (transactionin.component.ts:6599-6612); a line from an order has none, so the web neither stops
a larger
quantity nor a smaller one. The test asserts exactly that: 101 against an order of 100 is accepted without a
warning, and 40 as well. DECISION NEEDED: the sheet says "cannot add more than the order".
Row 9. "User cannot add more items": no handler exists (`isEditable` returns true,
transactionin.component.ts:6995),
so a second product can be added; asserted below as the next row accepting a product.
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.feedback import ToastKind
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE
from pages.purchase.documents.order_page import PurchaseOrderPage
from pages.purchase.documents.seed_documents import seed_draft, seed_order

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

ORDERED = Decimal(100)
ABOVE_ORDER = Decimal(101)
BELOW_ORDER = Decimal(40)
NO_WARNING_WAIT_MS = 2_500
OVER_MESSAGE = "Quantity should be less than or equals to"


@pytest.fixture
def bill_from_order(pharma_page: Page) -> Iterator[PurchaseBillEntryPage]:
    order_number = seed_order(pharma_page)
    draft = seed_draft(timestamp_label()).from_order(order_number)
    bills = PurchaseBillEntryPage(pharma_page)
    bills.begin(draft)
    bills.enter_entry_date(draft.entry_date)
    bills.complete_header(draft)
    bills.grid.expect_line_carried(0, draft.lines[0])
    yield bills
    bills.discard()
    PurchaseOrderPage(pharma_page).delete(order_number)


def test_quantity_above_the_order_is_accepted(bill_from_order: PurchaseBillEntryPage) -> None:
    bill_from_order.grid.type_quantity(0, ABOVE_ORDER)

    assert not bill_from_order.feedback.toast_appears(ToastKind.WARNING, NO_WARNING_WAIT_MS)
    assert bill_from_order.grid.product(0).quantity == ABOVE_ORDER


def test_quantity_below_the_order_is_accepted(bill_from_order: PurchaseBillEntryPage) -> None:
    bill_from_order.grid.type_quantity(0, BELOW_ORDER)

    assert not bill_from_order.feedback.toast_appears(ToastKind.WARNING, NO_WARNING_WAIT_MS)
    assert bill_from_order.grid.product(0).quantity == BELOW_ORDER


def test_another_product_can_still_be_added_to_a_bill_from_an_order(
    bill_from_order: PurchaseBillEntryPage,
) -> None:
    bill_from_order.grid.select_product(1, STANDARD_ITEM_CODE)

    bill_from_order.grid.expect_product_shown(1)
