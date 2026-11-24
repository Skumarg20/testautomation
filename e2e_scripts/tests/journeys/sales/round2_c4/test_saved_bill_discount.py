"""Sale bill row 111: reopen a saved bill and change the item discount.

The first discount column is a percentage of the line amount (dataCalculation.ts:429-436): 2 x 100 at
10% is 20.00,
changed to 25% it is 50.00; "Total Disc" in the footer shows it before and after the save and after reopening.
"""

from decimal import Decimal

import pytest

from pages.sale.documents.item_grid import FIRST_DISCOUNT
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, ITEM_REPEATED, HeldOptions
from pages.sale.manual.pharma_bill import RATE, PharmaBill
from pages.sale.manual.saved_bills import SavedBills

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-modification"),
    pytest.mark.xdist_group("chemist-tenant"),
]

QUANTITY = Decimal(2)
FIRST = Decimal(10)
CHANGED = Decimal(25)


def test_changed_discount_updates_the_total_discount_and_is_kept(
    options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills
) -> None:
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    options.hold(ITEM_REPEATED, "No")
    bill.start()
    bill.add_discounted_line(0, QUANTITY, FIRST)
    bill.expect_total_discount(QUANTITY * RATE * FIRST / 100)
    number = saved_bills.save(bill)

    bill.reopen(number)
    bill.document.grid.enter_discount(0, FIRST_DISCOUNT, CHANGED)
    bill.expect_total_discount(QUANTITY * RATE * CHANGED / 100)
    bill.save_changes()

    bill.reopen(number)
    bill.expect_total_discount(QUANTITY * RATE * CHANGED / 100)
