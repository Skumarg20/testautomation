"""Sale checklist rows 61, 62, 64, 65, 88 and 95 (barcode): the settings whose choices round 1 left open.

Choice texts are the API's lookups (`lookup.json`): 1084 Amount Calculation, 1117 Ask Bill No., 1154 Ask Net
Rate. Rules are cited on each test. Data is the test's own item (`desk.make_stock`).
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest
from playwright.sync_api import expect

from pages.accounting.waiting import appears_within
from pages.sale.manual.option_settings import HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.round2_c3.control_room_choice import Choice
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.sale_fields import (
    A_RATE,
    AMOUNT_CALCULATION,
    ASK_BILL_NO,
    ASK_NET_RATE,
    ASK_ORDER_NO,
    BATCHWISE,
    DEFAULT_BILLING_RATE,
    GST_CALCULATION,
    ITEM_WISE,
    RATES_FROM,
)
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)
TWO_PLACES = Decimal("0.01")
GST_PERCENT = Decimal(12)  # the owned item's tax category is "GST Sale - 12%"
TEN_PERCENT = Decimal(10)
NET_RATE = Decimal(90)
WINDOW_WAIT_MS = 4_000
ONE_BATCH = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),))
NET_RATE_BOX = 'input[id$="-netRate"]'


def test_net_amount_is_value_less_discount_plus_tax(desk: SaleDesk) -> None:
    """Row 61 (Net Amount): `calculateItemDisplayAmount` case '3' (dataCalculation.ts:762) gives rate x qty -
    discounts + the line's tax when the bill is exclusive. One piece, 10 % discount, 12 % GST: net =
    (rate - 10 %) x 1.12. Tax is taken on the discounted value (Decision needed Q-C3-9)."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(GST_CALCULATION, "Exclusive")
    desk.options.hold(AMOUNT_CALCULATION, "Net Amount")
    desk.sell(StockLine(item, item.batch_names[0], ONE))
    rate = desk.bill.picked_rate(0)

    desk.bill.type_discount(0, TEN_PERCENT)

    taxable = rate - rate * TEN_PERCENT / 100
    expected = (taxable + taxable * GST_PERCENT / 100).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    assert desk.bill.grid.amount(0) == expected


def test_left_arrow_key_option_moves_back_to_the_bill_number(desk: SaleDesk) -> None:
    """Row 62 (OnLeftArrowKey, value 1): the bill number is not a stop after the party, but Left arrow from
    the first grid cell returns to it (`setFocus`, processout.transaction.component.ts:3170-3177)."""
    desk.options.hold(ASK_BILL_NO, "OnLeftArrowKey")
    desk.bill.bill.open_with_party()
    page = desk.bill.bill.page
    desk.bill.grid.cell(0, "itemLinkID").click()

    page.keyboard.press("ArrowLeft")

    page.wait_for_function(
        "() => document.activeElement && document.activeElement.id.startsWith('askBillNo')"
    )


def test_star_key_option_shows_the_net_rate_box_only_after_the_star(desk: SaleDesk) -> None:
    """Row 64 (Ask on * Key): the net-rate box is hidden until * is pressed in the rate cell
    (`netrateask.component.ts:334`, askNetRate == 2)."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(ASK_NET_RATE, "Ask on * Key")
    desk.sell(StockLine(item, item.batch_names[0], ONE))
    page = desk.bill.bill.page
    desk.bill.grid.cell(0, "salePurchaseRate").click()
    assert not appears_within(page.locator(NET_RATE_BOX), WINDOW_WAIT_MS)

    page.keyboard.press("Shift+8")

    expect(page.locator(NET_RATE_BOX).first).to_be_visible()


def test_star_key_net_rate_becomes_the_row_rate_without_discount(desk: SaleDesk) -> None:
    """Row 88: a net rate of 90 typed in the * box and confirmed with Enter is applied (`hideAskNetRate`,
    netrateask.component.ts:261-275 sets isNetrateApplied and discount 0) and, on leaving the cell,
    becomes
    the rate (`onFocusOut`, :327-330)."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(ASK_NET_RATE, "Ask on * Key")
    desk.sell(StockLine(item, item.batch_names[0], ONE))
    page = desk.bill.bill.page
    desk.bill.grid.cell(0, "salePurchaseRate").click()
    page.keyboard.press("Shift+8")
    box = page.locator(NET_RATE_BOX).first
    box.fill(str(NET_RATE))

    box.press("Enter")
    box.press("Tab")

    assert desk.bill.picked_rate(0) == NET_RATE


@pytest.mark.parametrize("asked", ["Yes", "No"])
def test_order_number_window_opens_with_ctrl_c_only_when_asked(
    options: HeldOptions, bill: PharmaBill, asked: str
) -> None:
    """Row 65: Ctrl+C on a sale bill opens the Order No / Order Date window when Ask Order No., Order Date is
    Yes (processout.transaction.component.ts:15292-15295); the window takes a number and Save closes it
    (orderNoWindow.component.ts:71-84). What is stored is posted after the bill is saved (`saveOrder`,
    :16400), which no screen shows back."""
    options.hold(ASK_ORDER_NO, asked)
    bill.start()

    bill.page.keyboard.press("Control+C")

    order_box = bill.page.locator("#txtorderNo")
    if asked == "Yes":
        expect(order_box).to_be_visible()
        order_box.fill("QA-ORDER-1")
        bill.page.get_by_role("button", name="Save").last.click()
        expect(order_box).to_be_hidden()
    else:
        assert not appears_within(order_box, WINDOW_WAIT_MS)


@pytest.mark.parametrize(
    ("source", "expected"),
    [(ITEM_WISE, Decimal(150)), (BATCHWISE, Decimal(120))],
    ids=["item-wise", "batch-wise"],
)
def test_rate_by_barcode_follows_master_or_batch(desk: SaleDesk, source: str, expected: Decimal) -> None:
    """Row 95 (barcode): scanning the item's master barcode gives the same rate source as picking by hand
    (item wise 150 from the master, batch wise 120 from the batch: dataCalculation.ts:1664-1673). The item
    is created with the Control Room 'Barcode Required' = Master wise so its form has the barcode box."""
    desk.hold_choice(Choice("Barcode Required", "Master wise"))
    spec = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),), with_barcode=True)
    item = desk.make_stock(spec)
    desk.options.hold(RATES_FROM, source)
    desk.options.hold(DEFAULT_BILLING_RATE, A_RATE)
    desk.bill.bill.open_with_party()

    desk.bill.scan_barcode(0, item.code)

    assert desk.bill.picked_rate(0) == expected
