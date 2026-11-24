"""Sale checklist rows 25, 33, 95 (sale rate from the item master or the batch) and 26 (rate above M.R.P.).

Data is made by the test (`desk.make_stock`): one item whose master sale rate A is 150 and whose only batch
was bought with M.R.P. 180 and sale rate A 120, so the two sources can be told apart. The customer is a new
ledger with no rate class and not the cash party; otherwise `RatePick` and `RatePickBatchWise`
(`dataCalculation.ts:3042-3052`) would answer from the party's rate class or the cash rule (M.R.P.).

Rule: with "Rates from master/batch" = ItemWise (`rateFromMasterBatchDate == "1"`) the rate is the item
master's column named by "Default Billing Rate" (`RatePick`, :3042-3045); Batchwise takes the batch's rate A
(`RatePickBatchWise`, :3047-3051, option 5 for an ordinary party). Rate above M.R.P.:
`netrateask.component.ts:139-147` sets StopBilling and warns "As Per M.R.P Allowed Upto :" plus the row's
M.R.P. when "Billing rate greater then M.R.P on sale" (field 4124) is 2, and `onProcessOutSave` returns while
StopBilling is set (`processout.transaction.component.ts:10445`).
"""

from decimal import Decimal

import pytest

from pages.accounting.waiting import appears_within
from pages.sale.round2_c3.control_room_choice import Choice
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.sale_fields import A_RATE, BATCHWISE, DEFAULT_BILLING_RATE, ITEM_WISE, RATES_FROM
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)
MASTER_RATE_A = Decimal(150)
BATCH_RATE_A = Decimal(120)
BATCH_MRP = Decimal(180)
ABOVE_MRP = Decimal(181)
WARNING_TEXT = "As Per M.R.P Allowed Upto :"  # global.ts:18994 AlertMsg.greaterSaleRate
MRP_SETTING = "Billing rate greater then M.R.P on sale"  # ControlRoomDesignData.cs:1228, field 4124
# netrateask.component.ts:139 acts on the choice "2". The support article says "Yes" lets a rate above M.R.P.
# through, so "No" is the ban; the tenant's list is checked when the choice is made (Decision needed Q-C3-1).
MRP_BANNED = "No"
SAVE_WINDOW_LOOKUP_MS = 3_000

TWO_SOURCES = StockSpec(
    batches=(BatchSpec(mrp=BATCH_MRP, rate_a=BATCH_RATE_A),),
    master_rate_a=MASTER_RATE_A,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [(ITEM_WISE, MASTER_RATE_A), (BATCHWISE, BATCH_RATE_A)],
    ids=["item-wise-master-rate", "batch-wise-batch-rate"],
)
def test_sale_rate_is_picked_from_the_master_or_the_batch(
    desk: SaleDesk, source: str, expected: Decimal
) -> None:
    """Rows 25, 33 and 95 (manual entry): no rate is typed; the rate cell holds the master's rate A (150)
    item wise and the batch's rate A (120) batch wise, with Default Billing Rate on A-Rate."""
    item = desk.make_stock(TWO_SOURCES)
    desk.options.hold(RATES_FROM, source)
    desk.options.hold(DEFAULT_BILLING_RATE, A_RATE)

    desk.sell(StockLine(item, item.batch_names[0], ONE))

    assert desk.bill.picked_rate(0) == expected


def test_rate_above_mrp_is_refused_when_billing_above_mrp_is_banned(desk: SaleDesk) -> None:
    """Row 26: with the ban on, a rate of 181 on a batch whose M.R.P. is 180 shows the M.R.P. warning and the
    bill cannot be saved (no save window opens)."""
    item = desk.make_stock(TWO_SOURCES)
    desk.hold_choice(Choice(MRP_SETTING, MRP_BANNED))
    desk.options.hold(RATES_FROM, BATCHWISE)
    desk.sell(StockLine(item, item.batch_names[0], ONE))

    desk.bill.type_rate(0, ABOVE_MRP)

    desk.bill.bill.messages.expect_warning(WARNING_TEXT)
    desk.bill.bill.save()
    assert not appears_within(desk.bill.bill.document.save_window, SAVE_WINDOW_LOOKUP_MS)
    assert desk.bill.bill.is_open()
