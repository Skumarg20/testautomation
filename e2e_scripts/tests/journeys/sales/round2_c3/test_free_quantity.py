"""Sale checklist rows 72 and 73: the Free column of the sale bill.

Round 1 (`checklist/test_setting_behaviour.py::test_free_column_shows_only_when_free_quantity_is_required`)
showed the column follows "Free Quantity Required in Sale". Here a free quantity is typed and its effect
is read, on an item the test buys itself (one batch of 100).

Rules, in `processout.transaction.component.ts` and `dataCalculation.ts`:
- The row amount is quantity x rate; free is not in it (`calculateItemDisplayAmount`,
  dataCalculation.ts:750-757).
- "Free Quantity Required in Decimal" (lookup 1093): Always (1) lets the Free cell take decimals; If In
  Master (2) and As Per Master (3) allow them only for an item whose master allows decimal quantities
  (`isDecimalAllowedOnFree`, processout:13613-13620; the editor is the integer one otherwise, :7044-7048).
  A new item is whole-number, so only Always takes 1.5.
The Free column is drawn only for a company that is not bustype 5 (`!this.isChemist`, processout:6827); the
QA pharma company is not (memory: the QA login has no chemist company).
"""

from decimal import Decimal

import pytest

from pages.sale.documents.stock import StockLedger
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.sale_fields import FREE_QUANTITY, FREE_QUANTITY_DECIMAL
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

QUANTITY = Decimal(10)
FREE = Decimal(2)
ONE_BATCH = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),))


def test_free_quantity_is_kept_and_adds_nothing_to_the_amount(desk: SaleDesk) -> None:
    """Row 72: 10 sold with 2 free keep the Free cell at 2 and the row amount at 10 x rate."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(FREE_QUANTITY, "Yes")
    desk.sell(StockLine(item, item.batch_names[0], QUANTITY))

    desk.bill.type_free(0, "2")

    assert desk.bill.free_shown(0) == "2"
    assert desk.bill.grid.amount(0) == desk.bill.picked_rate(0) * QUANTITY


def test_free_quantity_leaves_stock_with_the_quantity(desk: SaleDesk) -> None:
    """Row 72, stock half: a saved bill of 10 with 2 free takes 12 from the item's stock (free pieces are
    issued like sold ones; the purchase side adds quantity plus free, `purchase/test_challan.py`). The
    sale-side rule is server work and not in the web source: Q-C3-4."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(FREE_QUANTITY, "Yes")
    ledger = StockLedger(desk.bill.bill.page)
    before = ledger.stock_of(item.code)
    desk.sell(StockLine(item, item.batch_names[0], QUANTITY))
    desk.bill.type_free(0, "2")

    desk.bills.save(desk.bill.bill.save_and_confirm)

    assert ledger.stock_of(item.code) == before - QUANTITY - FREE


@pytest.mark.parametrize(
    ("mode", "decimal_taken"),
    [("Always", True), ("If In Master", False), ("As Per Master", False)],
    ids=["always", "if-in-master", "as-per-master"],
)
def test_free_quantity_takes_decimals_as_the_setting_says(
    desk: SaleDesk, mode: str, decimal_taken: bool
) -> None:
    """Row 73: typing 1.5 in Free is kept only with Always; for a whole-number item the other two modes use
    the integer editor, which does not take the point."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(FREE_QUANTITY, "Yes")
    desk.options.hold(FREE_QUANTITY_DECIMAL, mode)
    desk.sell(StockLine(item, item.batch_names[0], QUANTITY))

    desk.bill.type_free(0, "1.5")

    assert ("." in desk.bill.free_shown(0)) == decimal_taken
