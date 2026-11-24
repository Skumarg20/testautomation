"""Sale checklist rows 45 (last bills, party wise), 63 (Ask Sale Type = No) and 92 (bill discount).

Row 45: the Control Room option "Last 5 details showing on right side party wise" (field 4323,
ControlRoomDesignData.cs:406; `LastFiveBillHideShow`, processout:1712) fills the right-hand panel
(`.sale-history`, processout html:1333-1360) with the party's address, last visit and previous bills once the
party is chosen (`getLastFiveBills`, processout:6036). The party is the owned customer with one saved bill.

Row 63: with Ask Sale Type at the time of Billing = No the walk after the party never stops on the sale type
field (processout:2236-2237 focuses txtSaleType only for 'T').

Row 92: the Bill Discount header field takes an amount, a changed amount and a cleared amount; the invoice
value falls by the discount and comes back when it is cleared (`totalbilldiscount`, dataCalculation.ts:772).
"""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.components.bill_totals import BillTotals
from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.checklist.focus import SALE_TYPE, grid_column
from pages.sale.checklist.holds import held_or_skip
from pages.sale.checklist.sale_setting import ASK_PARTY, ASK_SALE_TYPE, setting_held
from pages.sale.documents.item_grid import PRODUCT
from pages.sale.round2_c3.control_room_choice import Choice
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

LAST_FIVE_SETTING = "Last 5 details showing on right side party wise"
ONE_BATCH = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),))
FIRST_DISCOUNT_AMOUNT = Decimal(10)
SECOND_DISCOUNT_AMOUNT = Decimal(5)
ASK = "1"


@pytest.mark.parametrize("shown", ["Yes", "No"])
def test_previous_bills_panel_follows_the_last_five_setting(desk: SaleDesk, shown: str) -> None:
    """Row 45: with Yes the party's earlier bill fills the right-hand panel on a new bill; with No there is
    no panel."""
    desk.hold_choice(Choice(LAST_FIVE_SETTING, shown))
    item = desk.make_stock(ONE_BATCH)
    desk.sell(StockLine(item, item.batch_names[0], Decimal(1)))
    desk.bills.save(desk.bill.bill.save_and_confirm)

    desk.bill.start_for(desk.customer)

    panel = desk.bill.bill.page.locator(".sale-history")
    if shown == "Yes":
        expect(panel).to_be_visible()
    else:
        expect(panel).to_have_count(0)


def test_ask_sale_type_no_never_stops_on_the_sale_type(checklist_bill: ChecklistBill) -> None:
    """Row 63 (No): after the party the cursor goes to the grid, not to the sale type field."""
    checklist_bill.open_new()
    with setting_held(checklist_bill, ASK_PARTY, ASK), held_or_skip(checklist_bill, ASK_SALE_TYPE, "F"):
        checklist_bill.reopen()

        checklist_bill.choose_standard_party()

        checklist_bill.focus.press_until("Enter", (SALE_TYPE, grid_column(PRODUCT)), limit=6)
        assert not checklist_bill.focus.is_at(SALE_TYPE)


def test_bill_discount_can_be_added_changed_and_removed(desk: SaleDesk) -> None:
    """Row 92: the invoice value drops with a bill discount of 10, is higher with 5, and is back to the
    starting value when the discount is cleared."""
    item = desk.make_stock(ONE_BATCH)
    desk.sell(StockLine(item, item.batch_names[0], Decimal(1)))
    document = desk.bill.bill.document
    totals = BillTotals(document.page)
    start = totals.invoice_value()

    document.enter_bill_discount(FIRST_DISCOUNT_AMOUNT)
    with_ten = totals.invoice_value()
    document.enter_bill_discount(SECOND_DISCOUNT_AMOUNT)
    with_five = totals.invoice_value()
    document.enter_bill_discount(Decimal(0))

    assert with_ten < with_five < start
    assert totals.invoice_value() == start
