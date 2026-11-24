"""Multi-unit sale: Ajay rows 42, 43 and 180.

Setup, all the test's own: an item QA-<run>-Item with 100 pieces bought on its own purchase bill
(own_stocked_item),
then Control Room Multi Unit = Yes / 2 units / stock in unit 1 (`multi_unit_held`, restored afterwards) and a
second, bigger unit worth 10 pieces added to that item. Item, purchase bill and any sale bill are deleted
afterwards, so nothing is left behind and nothing here is `permanent`.
Arithmetic (processout.transaction.component.ts:13846-13849, helper.multiunitBaseSR): quantity = unit 2 x 10 +
unit 1; amount = quantity x rate per piece (rate in unit = Unit1). Rate 100 per piece.
"""

from decimal import Decimal

import pytest

from pages.inventory.round2_c1.own_item import OwnItem
from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.stock import StockLedger
from pages.sale.manual.pharma_bill import RATE
from pages.sale.round2_c1.cells import UNIT_1, UNIT_2
from pages.sale.round2_c1.deal_math import base_quantity, multi_unit_amount
from pages.sale.round2_c1.desk import Desk

PIECES_PER_BIGGER_UNIT = 10
pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def _enter_units(desk: Desk, item: OwnItem, units: tuple[int, int]) -> None:
    """`units` is (unit 2 = bigger, unit 1 = pieces)."""
    bill = desk.bill
    bill.start()
    bill.document.grid.select_product(0, item.code)
    bill.document.grid.choose_batch(0, item.batch)
    desk.cells.type_into(0, UNIT_2, Decimal(units[0]))
    desk.cells.type_into(0, UNIT_1, Decimal(units[1]))
    bill.type_rate(0, f"{RATE:f}")
    bill.accept_low_rate_if_asked()


def test_unit_two_and_unit_one_make_one_stored_quantity(two_unit_item: OwnItem, desk: Desk) -> None:
    """Row 42: 1 bigger unit + 5 pieces is 15 pieces; the line amount shows 15 x 100."""
    _enter_units(desk, two_unit_item, (1, 5))

    desk.bill.expect_gross(multi_unit_amount(base_quantity(1, 5, PIECES_PER_BIGGER_UNIT), RATE))


def test_amount_follows_the_conversion(two_unit_item: OwnItem, desk: Desk) -> None:
    """Row 43: 2 bigger units + 0 pieces is 20 pieces; the amount is 20 x 100."""
    _enter_units(desk, two_unit_item, (2, 0))

    desk.bill.expect_gross(multi_unit_amount(base_quantity(2, 0, PIECES_PER_BIGGER_UNIT), RATE))


def test_alternate_unit_sale_takes_converted_stock_from_the_batch(two_unit_item: OwnItem, desk: Desk) -> None:
    """Row 180: 1 bigger unit + 5 pieces sold from the item's own batch lowers its stock by 15."""
    quantity = Decimal(base_quantity(1, 5, PIECES_PER_BIGGER_UNIT))
    sold = (ProductLine(two_unit_item.code, two_unit_item.batch, quantity, RATE),)
    ledger = StockLedger(desk.bill.page)
    before = ledger.snapshot(sold)
    _enter_units(desk, two_unit_item, (1, 5))

    desk.saved.save(desk.bill)

    ledger.expect_sold(before, sold)
