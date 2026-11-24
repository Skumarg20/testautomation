"""Purchase checklist rows 29, 30 and 55: item discounts and bill discount on a purchase line.

The expected "Total Disc" is worked out by `pages/purchase/checklist/line_math.py` from dataCalculation.ts:
discount 1 = (amount - volume discounts) x d1%; discount 2 = the same less discount 1 first (:419-440).
The bill discount is a percentage of the goods (as in test_purchase_saved_values.py). One line, 10 pieces at
100, so the amount is 1000. The discount columns are switched on in the Control Room; a bill whose discount
cell is not drawn is skipped, not failed.
"""

from decimal import Decimal

import pytest

from pages.purchase.checklist.cell_focus import CellFocus
from pages.purchase.checklist.discount_readout import DiscountReadout
from pages.purchase.checklist.line_math import item_discounts
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.line_items import (
    STANDARD_EXPIRY,
    STANDARD_ITEM_CODE,
    DiscountColumn,
    PurchaseLineItem,
)
from pages.purchase.documents.seed_documents import seed_draft

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

QUANTITY = Decimal(10)
RATE = Decimal(100)
AMOUNT = QUANTITY * RATE


def _line(first: int, second: int = 0) -> PurchaseLineItem:
    return PurchaseLineItem(
        STANDARD_ITEM_CODE,
        QUANTITY,
        rate=RATE,
        expiry_serial=STANDARD_EXPIRY,
        batch=timestamp_label(),
        discounts={DiscountColumn.DISCOUNT_1: Decimal(first), DiscountColumn.DISCOUNT_2: Decimal(second)},
    )


def _bill_with_line(bill: PurchaseBillEntryPage, line: PurchaseLineItem) -> None:
    bill.fill_lines(bill_draft(line))
    if not CellFocus(bill.page).first_discount_is_shown(0):
        pytest.skip(
            "checklist rows 29, 30, 55: needs the item discount columns switched on in the Control Room"
        )


def bill_draft(line: PurchaseLineItem) -> PurchaseDraft:
    return seed_draft().with_lines((line,))


def test_first_item_discount_is_a_share_of_the_amount(new_bill: PurchaseBillEntryPage) -> None:
    _bill_with_line(new_bill, _line(first=10))

    DiscountReadout(new_bill.page).expect_total(item_discounts(AMOUNT, (Decimal(10), Decimal(0))).total)


def test_second_item_discount_is_taken_after_the_first(new_bill: PurchaseBillEntryPage) -> None:
    _bill_with_line(new_bill, _line(first=10, second=5))

    DiscountReadout(new_bill.page).expect_total(item_discounts(AMOUNT, (Decimal(10), Decimal(5))).total)


def test_item_discount_can_be_changed_and_removed(new_bill: PurchaseBillEntryPage) -> None:
    _bill_with_line(new_bill, _line(first=10))
    readout = DiscountReadout(new_bill.page)
    readout.expect_total(item_discounts(AMOUNT, (Decimal(10), Decimal(0))).total)

    new_bill.grid.enter_discounts(0, _line(first=20))
    readout.expect_total(item_discounts(AMOUNT, (Decimal(20), Decimal(0))).total)

    new_bill.grid.enter_discounts(0, _line(first=0))
    readout.expect_total(Decimal(0))


def test_bill_discount_can_be_added_changed_and_removed(new_bill: PurchaseBillEntryPage) -> None:
    new_bill.fill_lines(bill_draft(_line(first=0)))
    readout = DiscountReadout(new_bill.page)

    new_bill.footer.enter_bill_discount(Decimal(10))
    readout.expect_total(AMOUNT * Decimal(10) / 100)

    new_bill.footer.enter_bill_discount(Decimal(20))
    readout.expect_total(AMOUNT * Decimal(20) / 100)

    new_bill.footer.enter_bill_discount(Decimal(0))
    readout.expect_total(Decimal(0))
