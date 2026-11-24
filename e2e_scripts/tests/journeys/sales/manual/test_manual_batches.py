"""Manual cases 67, 79, 112: the same item in two batches, and changing a saved bill's batch.

The batches of item 44646015 are read from the batch window at run time; a company whose item has only the
one batch skips with that reason (nothing is invented). Amounts are quantity x rate of 100 with "Amount
Calculation On Billing" at Rate*Qty (`dataCalculation.ts:750-757`); the item's total stock does not change
when a bill moves from one batch to another (the same quantity is still sold), which is read from the item
list as the ported TC_SM_001 does. Saved bills are deleted by the `saved_bills` fixture.
"""

from decimal import Decimal

import pytest

from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.stock import StockLedger
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, ITEM_REPEATED, HeldOptions
from pages.sale.manual.pharma_bill import BATCH, ITEM, RATE, PharmaBill
from pages.sale.manual.saved_bills import SavedBills

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)
TWO = Decimal(2)


@pytest.fixture
def other_batch(options: HeldOptions, bill: PharmaBill) -> str:
    """A second batch of the item, read from the batch window; the test is skipped when there is none."""
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    options.hold(ITEM_REPEATED, "No")
    bill.start()
    names = bill.batch_names_of_item()
    bill.leave_without_saving()
    others = [name for name in names if name != BATCH]
    if not others:
        pytest.skip(f"item {ITEM} has only the batch {BATCH}")
    return others[0]


def test_two_batches_of_one_item_sit_on_two_rows(bill: PharmaBill, other_batch: str) -> None:
    """Rows 67 and 79: each row keeps its batch, its quantity and its amount."""
    bill.start()
    bill.add_line_in_batch(0, BATCH, ONE)
    bill.add_line_in_batch(1, other_batch, TWO)

    bill.expect_batch_in_row(0, BATCH)
    bill.expect_batch_in_row(1, other_batch)
    bill.expect_quantities([ONE, TWO])
    bill.expect_gross((ONE + TWO) * RATE)


def test_changing_the_batch_of_a_saved_bill_keeps_the_stock_taken(
    bill: PharmaBill, saved_bills: SavedBills, other_batch: str
) -> None:
    """Row 112: the bill shows the new batch; the item's stock is still down by the quantity sold."""
    sold = (ProductLine(ITEM, BATCH, ONE, RATE),)
    ledger = StockLedger(bill.page)
    before = ledger.snapshot(sold)
    bill.start()
    bill.add_line(0, ONE)
    number = saved_bills.save(bill)

    bill.reopen(number)
    bill.change_batch(0, other_batch)
    bill.save_changes()

    ledger.expect_sold(before, sold)
    bill.reopen(number)
    bill.expect_batch_in_row(0, other_batch)
