"""Lot Rate: Sale Checklist rows 79 and 90 (Lot Rate Calculation).

With "Lot Rate Calculation" = F7 Key, F7 in the rate cell opens the Lot Rate window
(netrateask.component.ts:339-
342) and the new rate is: Percentage -> rate / (100 + p) x 100; Rate (a deal q + f) -> rate / (q + f) x q
(lotRate.component.ts:206-216, shown to 2 decimals when "decimal for sale rate" is 2). KB careportal
"What is the
Process of Lot Rate": rate 100 with 10 % -> 90.91; deal 10 + 1 -> 90.91.
Question for the product owner: the "Scheme" type of the window keeps the rate unchanged in this code path
(:210-212), so it is not asserted.
"""

from decimal import Decimal

import pytest

from pages.sale.manual.option_settings import HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.round2_c1.cells import RATE, GridCells
from pages.sale.round2_c1.deal_math import lot_rate_by_deal, lot_rate_by_percentage
from pages.sale.round2_c1.lot_rate_window import LotRateWindow
from pages.settings.round2_c1.fields import LOT_RATE_CALCULATION

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

BILLED_RATE = Decimal(100)


@pytest.fixture
def f7_lot_rate(options: HeldOptions) -> None:
    options.hold(LOT_RATE_CALCULATION, "F7 Key")


def _ready_rate_cell(bill: PharmaBill) -> LotRateWindow:
    bill.start()
    bill.pick_item(0, Decimal(10))
    bill.type_rate(0, f"{BILLED_RATE:f}")
    bill.accept_low_rate_if_asked()
    window = LotRateWindow(bill.page)
    window.open_from_rate_cell(0)
    return window


def test_lot_rate_by_percentage(f7_lot_rate: None, bill: PharmaBill, cells: GridCells) -> None:
    """Rows 79 and 90: rate 100, Lot % 10 -> 100 / 110 x 100 = 90.91."""
    window = _ready_rate_cell(bill)

    window.by_percentage(Decimal(10))

    cells.expect_value(0, RATE, lot_rate_by_percentage(BILLED_RATE, Decimal(10)))


def test_lot_rate_by_deal(f7_lot_rate: None, bill: PharmaBill, cells: GridCells) -> None:
    """Rows 79 and 90: rate 100, deal 10 + 1 -> 100 / 11 x 10 = 90.91."""
    window = _ready_rate_cell(bill)

    window.by_deal(10, 1)

    cells.expect_value(0, RATE, lot_rate_by_deal(BILLED_RATE, (10, 1)))
