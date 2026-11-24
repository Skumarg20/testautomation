"""Sale checklist row 81: GST cess as a percentage and as an amount per unit.

Rule, `dataCalculation.ts:3484-3500` (calculateItemCess) and :3516-3535 (calaculateCessInAmount), for an
exclusive-tax bill with no discount: cess = amount x cess % / 100 + additional cess x quantity. The two
item fields are "Cess in %" and "Additional Cess Amount" (Create Item `#txtcessper`, `#txtcessper2`), shown
only while the Control Room "Surcharge/Octroi/GST Cess" window has them on (`isCessVisible`,
`isAdditionalCessVisible`, rateinfo-setting.html:225-245). The rate the app picks is read as an input; the
expected cess is worked out here.
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest

from pages.sale.checklist.tax_panel import TaxPanel
from pages.sale.round2_c3.configure_settings import CESS_AMOUNT, CESS_PERCENT
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.sale_fields import GST_CALCULATION
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

QUANTITY = Decimal(10)
HUNDRED = Decimal(100)
TWO_PLACES = Decimal("0.01")


@pytest.mark.parametrize(
    ("percent", "per_unit"),
    [(Decimal(5), None), (None, Decimal(2))],
    ids=["cess-percentage", "cess-amount-per-unit"],
)
def test_cess_follows_the_percentage_or_the_amount_on_the_item(
    desk: SaleDesk, percent: Decimal | None, per_unit: Decimal | None
) -> None:
    """Row 81: 10 pieces of an item with cess 5 % (or 2 a piece) show CESS of rate x 10 x 5 / 100 (or 20)."""
    desk.options.hold(CESS_PERCENT, "Yes")
    desk.options.hold(CESS_AMOUNT, "Yes")
    desk.options.hold(GST_CALCULATION, "Exclusive")
    spec = StockSpec(
        batches=(BatchSpec(Decimal(180), Decimal(120)),), cess_percent=percent, cess_per_unit=per_unit
    )
    item = desk.make_stock(spec)

    desk.sell(StockLine(item, item.batch_names[0], QUANTITY))

    value = desk.bill.picked_rate(0) * QUANTITY
    expected = value * (percent or Decimal(0)) / HUNDRED + (per_unit or Decimal(0)) * QUANTITY
    shown = TaxPanel(desk.bill.bill.page).tax("CESS")
    assert shown == expected.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
