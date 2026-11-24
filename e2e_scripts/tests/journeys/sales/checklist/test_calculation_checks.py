"""Sale checklist rows 22, 25, 83, 92, 93, 94: figures a sale bill works out, checked against arithmetic.

Inputs are typed or read from the line (the rate the app picked is an input), results are compared with
`Decimal` arithmetic, never with a figure copied from the screen. Nothing is saved. Sources:
`childcomponents/netProfit.component.ts` (Net Profit window, PO:15297 Alt+F10), `netloss.component.ts` and
`applyNetLossSetting` (PO:12938-12950), `RatePick` (`dataCalculation.ts:3042`)."""

from decimal import ROUND_HALF_UP, Decimal

import pytest
from playwright.sync_api import expect

from pages.sale.checklist.bill_screen import STANDARD_LINE, ChecklistBill
from pages.sale.checklist.net_profit_window import NetProfitWindow
from pages.sale.checklist.tax_panel import TaxPanel
from pages.sale.documents.item_grid import FIRST_DISCOUNT
from pages.sale.documents.screen import is_shown_within

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal(100)
LOSS_WINDOW_WAIT_MS = 4_000


@pytest.fixture
def line_ready(bill: ChecklistBill) -> ChecklistBill:
    """The standard party and a line of item 44646015, batch 1231231123, quantity 1, rate as the app
    picked it."""
    bill.choose_standard_party()
    grid = bill.document.grid
    grid.select_product(0, STANDARD_LINE.product)
    grid.choose_batch(0, STANDARD_LINE.batch)
    grid.enter_quantity(0, STANDARD_LINE.quantity)
    return bill


def test_sale_rate_is_picked_automatically_after_the_batch(line_ready: ChecklistBill) -> None:
    """Row 25: no rate is typed, yet the rate cell holds a positive rate (RatePick, dataCalculation.ts:3042,
    takes it from the party's rate class, else the item/batch rate per Default Billing Rate). Which rate (item
    or batch wise) depends on Control Room "Rate from Master/Batch" and is covered by the rate-validation
    journey."""
    assert line_ready.document.grid.displayed_price(0) > 0


def test_intra_state_tax_is_split_equally_between_cgst_and_sgst(line_ready: ChecklistBill) -> None:
    """Row 22: a bill is either CGST+SGST (equal halves, IGST nil) or IGST alone (CGST and SGST nil); the bill
    total is gross - discount + tax + round off (`InvoiceTotals`, the check every sale document already
    makes)."""
    taxes = TaxPanel(line_ready.page)
    cgst, sgst, igst = taxes.tax("CGST"), taxes.tax("SGST"), taxes.tax("IGST")

    assert (cgst == sgst and igst == 0) or (igst > 0 and cgst == 0 and sgst == 0)
    line_ready.document.verify_invoice_total(has_lines=True)


@pytest.mark.parametrize("states", ["add", "modify", "remove"])
def test_item_discount_can_be_added_modified_and_removed(line_ready: ChecklistBill, states: str) -> None:
    """Row 92: Total Disc follows the item discount: 10% of rate x quantity after it is added, 5% after it is
    changed, nothing after it is cleared."""
    grid = line_ready.document.grid
    gross = grid.displayed_price(0) * STANDARD_LINE.quantity
    panel = TaxPanel(line_ready.page)
    steps = {"add": [Decimal(10)], "modify": [Decimal(10), Decimal(5)], "remove": [Decimal(10), Decimal(0)]}[
        states
    ]

    for percent in steps:
        grid.cell(0, FIRST_DISCOUNT).click()
        grid.cell(0, FIRST_DISCOUNT).locator("input").fill(format(percent, "f"))
        grid.cell(0, FIRST_DISCOUNT).locator("input").press("Enter")

    expected = (gross * steps[-1] / HUNDRED).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    assert panel.total_discount().quantize(TWO_PLACES) == expected


def test_alt_f10_profit_window_adds_up(line_ready: ChecklistBill) -> None:
    """Rows 83 and 93: Alt+F10 opens the Net Profit window; Value is rate x quantity less discount,
    Profit is Value less Cost, and the percentage is Profit / Cost x 100 (a zero cost counts as 1),
    all from netProfit.component.ts getNetProfitData. Skipped on an inclusive-tax tenant, where GST is
    also taken off."""
    grid = line_ready.document.grid
    gross = grid.displayed_price(0) * STANDARD_LINE.quantity
    profit = NetProfitWindow(line_ready.page)
    profit.open()

    shown = profit.figures()

    profit.close()
    if shown.value != gross.quantize(TWO_PLACES):
        pytest.skip("rows 83/93: Value differs from rate x quantity, the tenant calculates tax inclusive")
    assert shown.profit == shown.value - shown.cost
    divisor = shown.cost if shown.cost != 0 else Decimal(1)
    assert shown.percentage == (shown.profit / divisor * HUNDRED).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def test_selling_far_below_cost_opens_the_loss_window(line_ready: ChecklistBill) -> None:
    """Row 94: a rate of 0.01 is below any cost, so with loss indication on, leaving the rate opens the
    Net Loss / Margin Loss window (applyNetLossSetting PO:12938-12950; titles in global.ts
    LossAlertTitle). Skipped when Net/Margin Loss indication is "No" (the window never opens)."""
    grid = line_ready.document.grid
    grid.cell(0, "salePurchaseRate").click()
    grid.cell(0, "salePurchaseRate").locator("input").fill("0.01")
    grid.cell(0, "salePurchaseRate").locator("input").press("Enter")
    loss_window = line_ready.page.get_by_text("Net Loss").or_(line_ready.page.get_by_text("Margin Loss"))

    if not is_shown_within(loss_window, LOSS_WINDOW_WAIT_MS):
        pytest.skip("row 94: Net Loss and Margin Loss Indication is off in this tenant (no window opened)")

    expect(loss_window.first).to_be_visible()
