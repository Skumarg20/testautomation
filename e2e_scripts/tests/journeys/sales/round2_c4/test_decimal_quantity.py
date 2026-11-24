"""Sale bill row 47: decimals in the quantity of a sale line.

What the web does (not what the sheet hopes for):
- the quantity editor takes up to 2 decimals whatever the unit (mask 'Ndecimal', global.ts:19866, with
  `decimalMask` precision 2: template.sale.decimalformat.ts:62,111); typing 2.5 keeps 2.5 and raises no
message;
- "Decimal for Unit is disabled" (global.ts:19379) is raised only by F8 in the quantity cell of an item whose
  unit does not allow decimals (`IsUnitInDecimal` false: template.sale.decimalformat.ts:252-259).
The item is made by the test (unit PCS, part C3's `OwnedStock`); that PCS is a whole unit is an assumption.
"""

import re
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.item_grid import QUANTITY
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.round2_c3.owned_stock import BatchSpec, StockFactory, StockSpec

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

DECIMAL_QUANTITY = Decimal("2.5")
RATE = Decimal(150)
DECIMAL_DISABLED = "Decimal for Unit is disabled"


def test_two_and_a_half_is_kept_in_the_quantity_without_a_message(bill: PharmaBill) -> None:
    bill.start()
    bill.pick_item(0, DECIMAL_QUANTITY)

    expect(bill.document.grid.cell(0, QUANTITY)).to_have_text(re.compile(r"^\s*2\.5(0)?\s*$"))
    bill.messages.expect_no_warning(DECIMAL_DISABLED)


def test_f8_in_the_quantity_of_a_whole_unit_item_says_decimal_is_disabled(
    bill: PharmaBill, stock_factory: StockFactory
) -> None:
    item = stock_factory(StockSpec(batches=(BatchSpec(mrp=Decimal(200), rate_a=RATE),)))
    bill.start()
    bill.document.add_line(0, ProductLine(item.code, item.batch_names[0], Decimal(1), RATE))
    cell = bill.document.grid.cell(0, QUANTITY)
    cell.dblclick()

    cell.locator("input").press("F8")

    bill.messages.expect_warning(DECIMAL_DISABLED)
