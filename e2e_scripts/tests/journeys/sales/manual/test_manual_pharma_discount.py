"""Manual case 102: an item discount follows a changed quantity.

The first discount column is a percentage of the line amount (`dataCalculation.ts:429-436`, "Y" mode), so
10% on 3 x 100 is 30.00 and, after the quantity becomes 5, 10% on 5 x 100 is 50.00. The figure read is the
footer's "Total Disc". Nothing is saved.
"""

from decimal import Decimal

import pytest

from pages.sale.manual.pharma_bill import RATE, PharmaBill

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

DISCOUNT_PERCENT = Decimal(10)
FIRST_QUANTITY = Decimal(3)
CHANGED_QUANTITY = Decimal(5)


def test_item_discount_is_recalculated_after_a_quantity_change(bill: PharmaBill) -> None:
    bill.start()
    bill.add_discounted_line(0, FIRST_QUANTITY, DISCOUNT_PERCENT)
    bill.expect_total_discount(FIRST_QUANTITY * RATE * DISCOUNT_PERCENT / 100)

    bill.change_quantity(0, CHANGED_QUANTITY)

    bill.expect_total_discount(CHANGED_QUANTITY * RATE * DISCOUNT_PERCENT / 100)
