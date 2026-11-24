"""Multi-unit purchase: Purchase Checklist rows 16-21 and 23.

Setup: an own item QA-<run>-Item with a second unit worth 10 pieces and Multi Unit Yes / 2 units / stock in
unit 1 (conftest; everything is put back or deleted afterwards). The stored quantity is unit 2 x 10
+ unit 1 (transactionin.component.ts:4080), so
"unit 2 = 1, unit 1 = 5" is 15 pieces, billed at the rate per piece.
"""

from decimal import Decimal

import pytest

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.round2_c1.two_unit_line import FREE, UNIT_1, UNIT_2, TwoUnitLine
from pages.sale.round2_c1.deal_math import base_quantity, multi_unit_amount

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("purchase-itc"),
    pytest.mark.xdist_group("chemist-tenant"),
]

PIECES = 10
RATE = Decimal(100)


def _line(bill: PurchaseBillEntryPage) -> TwoUnitLine:
    return TwoUnitLine(bill.page)


def test_quantity_can_be_entered_in_unit_two_and_unit_one(two_unit_bill: PurchaseBillEntryPage) -> None:
    """Row 16: an item with two units offers both cells; row 17/18: they are headed Unit-2 and Unit-1."""
    _line(two_unit_bill).expect_both_unit_cells()
    _line(two_unit_bill).expect_headers()


def test_entered_units_are_kept_as_typed(two_unit_bill: PurchaseBillEntryPage) -> None:
    """Rows 19 and 20: unit 2 = 1 and unit 1 = 5 stay 1 and 5 in their cells."""
    line = _line(two_unit_bill)

    line.enter(UNIT_2, Decimal(1))
    line.enter(UNIT_1, Decimal(5))

    line.expect_value(UNIT_2, Decimal(1))
    line.expect_value(UNIT_1, Decimal(5))


def test_back_end_quantity_is_the_converted_sum(two_unit_bill: PurchaseBillEntryPage) -> None:
    """Row 21: 1 x 10 + 5 = 15 pieces, so the line amount at 100 a piece is 1500."""
    line = _line(two_unit_bill)
    line.enter(UNIT_2, Decimal(1))
    line.enter(UNIT_1, Decimal(5))

    two_unit_bill.grid.enter_rate(0, RATE)

    assert two_unit_bill.grid.gross_amount() == multi_unit_amount(base_quantity(1, 5, PIECES), RATE)


def test_free_quantity_goes_into_the_smaller_unit(two_unit_bill: PurchaseBillEntryPage) -> None:
    """Row 23: a free quantity of 3 is entered in the free cell, in unit 1, and is not billed."""
    line = _line(two_unit_bill)
    line.enter(UNIT_2, Decimal(1))
    line.enter(UNIT_1, Decimal(5))
    line.enter(FREE, Decimal(3))

    two_unit_bill.grid.enter_rate(0, RATE)

    line.expect_value(FREE, Decimal(3))
    assert two_unit_bill.grid.gross_amount() == multi_unit_amount(base_quantity(1, 5, PIECES), RATE)
