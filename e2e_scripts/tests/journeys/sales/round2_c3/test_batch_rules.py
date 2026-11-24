"""Sale checklist rows 29 (near-expiry batch) and 71 (order of the batch window).

Both are tried on an item the test buys itself, in three batches whose names, expiries and purchase dates
are in different orders, so each ordering rule gives a different list.

Row 29, `Component/Transaction/InverntoryTransaction/childcomponents/processinbatch.component.ts:1085-1089`:
choosing a batch in the sale's batch window with "Near expired items on billing" = Ban (2) and the batch's
expiry within "Calculate Near Expiry Days" of the bill date (`Helper.services.ts:13881` expcheck) is refused
with "Ban Near Expiry For Billing" (global.ts:19456). The batches here expire in 600 to 900 days, so the
days setting is raised to 1000 for the test (and put back); a batch that is already past its expiry cannot
be bought (the purchase bill refuses it, `transactionin.component.ts:11930`), see scenarios.md Q-C3-2.

Row 71, `margerpdal/BatchAndStockOpeningBalance2.cs:313-350`: the batch list is read ordered by 1 Expiry,
2 MFG Date, 3 FIFO (entry) Date, 4 Batch Name, all ascending, per "Batch window index on".
"""

from decimal import Decimal

import pytest

from pages.sale.round2_c3.configure_settings import NEAR_EXPIRED, NEAR_EXPIRY_DAYS
from pages.sale.round2_c3.control_room_choice import Choice
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.sale_fields import BATCH_WINDOW_INDEX
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)
BAN_WARNING = "Ban Near Expiry For Billing"  # global.ts:19456 AlertMsg.banBatch
PURCHASE_BACK_DATE = "Purchase BackDate Billing"
WIDE_NEAR_EXPIRY_DAYS = "1000"
RATE = Decimal(120)

# Bought first to last: C, A, B. Expiry soonest to latest: B (600 d), C (730 d), A (900 d).
NAME_C, NAME_A, NAME_B = "QAC", "QAA", "QAB"
THREE_BATCHES = StockSpec(
    batches=(
        BatchSpec(Decimal(180), RATE, expiry_in_days=730, name=NAME_C, entry_days_ago=2),
        BatchSpec(Decimal(180), RATE, expiry_in_days=900, name=NAME_A, entry_days_ago=1),
        BatchSpec(Decimal(180), RATE, expiry_in_days=600, name=NAME_B),
    ),
)
ORDERS = {
    "Expiry": [NAME_B, NAME_C, NAME_A],
    "FIFO Date": [NAME_C, NAME_A, NAME_B],
    "Batch Name": [NAME_A, NAME_B, NAME_C],
}


@pytest.mark.parametrize("index_on", list(ORDERS), ids=["expiry", "fifo-date", "batch-name"])
def test_batch_window_lists_batches_in_the_chosen_order(desk: SaleDesk, index_on: str) -> None:
    """Row 71 (Expiry, FIFO Date, Batch Name): with the index on each choice the window lists the three
    batches in that order. MFG Date is not tried: the purchase bill cannot type an MFG date (Q-C3-3)."""
    desk.hold_choice(Choice(PURCHASE_BACK_DATE, "Yes"))
    item = desk.make_stock(THREE_BATCHES)
    desk.options.hold(BATCH_WINDOW_INDEX, index_on)
    desk.bill.start_for(desk.customer)

    listed = desk.bill.batch_order(item)

    assert listed == ORDERS[index_on]


def test_near_expiry_batch_is_refused_when_near_expiry_is_banned(desk: SaleDesk) -> None:
    """Row 29 (near-expired item): with Ban and a wide near-expiry window, picking the batch shows the ban
    warning and the row keeps no batch."""
    item = desk.make_stock(THREE_BATCHES)
    desk.options.hold(NEAR_EXPIRY_DAYS, WIDE_NEAR_EXPIRY_DAYS)
    desk.options.hold(NEAR_EXPIRED, "Ban")
    desk.bill.start_for(desk.customer)
    desk.bill.grid.select_product(0, item.code)

    desk.bill.try_batch(0, item.batch_names[0])

    desk.bill.bill.messages.expect_warning(BAN_WARNING)


def test_near_expiry_batch_is_billable_when_near_expiry_only_indicates(desk: SaleDesk) -> None:
    """Row 29 (control): with Indicate the same batch is accepted into the row."""
    item = desk.make_stock(THREE_BATCHES)
    desk.options.hold(NEAR_EXPIRY_DAYS, WIDE_NEAR_EXPIRY_DAYS)
    desk.options.hold(NEAR_EXPIRED, "Indicate")

    desk.sell(StockLine(item, item.batch_names[0], ONE))

    desk.bill.bill.messages.expect_no_warning(BAN_WARNING)
    desk.bill.bill.expect_batch_in_row(0, item.batch_names[0])
