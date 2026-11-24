"""Purchase checklist rows 15, 25 and 28: where the cursor goes after the batch, the free and the rate.

The sheet gives the order batch, quantity, free, rate, discount. An item with an expiry column has the expiry
cell right after the batch, so the expiry is entered first and the quantity cell is checked after it.
Unverified live: the order of the cells is the sheet's; the locators are those of `EntryGrid`.
"""

from decimal import Decimal

import pytest

from pages.purchase.checklist.cell_focus import CellFocus
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.line_items import STANDARD_EXPIRY, STANDARD_ITEM_CODE

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

QUANTITY = Decimal(10)
FREE = Decimal(2)
RATE = Decimal(100)


def _line_up_to_the_quantity(bill: PurchaseBillEntryPage) -> None:
    bill.grid.select_product(0, STANDARD_ITEM_CODE)
    bill.grid.type_batch(0, timestamp_label())
    bill.grid.enter_expiry(0, STANDARD_EXPIRY)


def test_cursor_goes_to_the_quantity_after_the_batch(new_bill: PurchaseBillEntryPage) -> None:
    _line_up_to_the_quantity(new_bill)

    CellFocus(new_bill.page).expect_on_quantity(0)


def test_cursor_goes_to_the_rate_after_the_free_quantity(new_bill: PurchaseBillEntryPage) -> None:
    _line_up_to_the_quantity(new_bill)
    new_bill.grid.enter_quantity(0, QUANTITY)

    new_bill.grid.enter_free(0, FREE)

    CellFocus(new_bill.page).expect_on_rate(0)


def test_cursor_goes_to_the_first_discount_after_the_rate_when_discounts_are_on(
    new_bill: PurchaseBillEntryPage,
) -> None:
    _line_up_to_the_quantity(new_bill)
    new_bill.grid.enter_quantity(0, QUANTITY)
    new_bill.grid.enter_free(0, FREE)
    focus = CellFocus(new_bill.page)
    if not focus.first_discount_is_shown(0):
        pytest.skip("checklist row 28: needs the item discount column switched on in the Control Room")

    new_bill.grid.enter_rate(0, RATE)

    focus.expect_on_first_discount(0)
