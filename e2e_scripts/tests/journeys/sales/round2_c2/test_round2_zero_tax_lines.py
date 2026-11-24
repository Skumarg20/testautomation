"""Ajay rows 76, 90 (taxable + nil-rated) and 91 (taxable + non-GST): GST is charged on the taxable line only.

The test makes its own tax category with the zero type under test (Nil Rated; also Exempted and Zero Rated for
row 91, because the item form has no separate "non-GST" flag: createitem.component.html holds only Tax
Category, and the closest zero-rate types are those of add.taxcategory.component.html:60-62; Decision needed,
see scenarios.md). The taxable line is the garments "Sample Item" (5%, rate 100, quantity 3) sold to the
intra-state party "Ajay": CGST 7.50 + SGST 7.50 (test_data.gst_calc). The zero-tax item adds its goods
value and
no tax. Nothing is saved. The item has opening stock so the bill can sell it, which is why it stays behind.
"""

from collections.abc import Callable, Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.components.bill_totals import BillTotals
from pages.masters.round2_c2.owned_items import OwnedItems
from pages.masters.round2_c2.tax_category import OwnedTaxCategories, ZeroTaxType
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from test_data.gst_calc import line_tax
from test_data.models import ItemMasterSpec

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
    pytest.mark.permanent("an item with opening stock (QA-<run>-Item1) and its tax category stay"),
]

TAXABLE_ITEM = "Sample Item"
TAXABLE_RATE = Decimal(100)
TAXABLE_SLAB = Decimal(5)
QUANTITY = Decimal(3)
ZERO_QUANTITY = Decimal(2)
OPENING = Decimal(10)
INTRA_STATE_PARTY = "Ajay"


@pytest.fixture
def zero_tax_item(
    guarded_page: Page, items: OwnedItems, run_id: str
) -> Iterator[Callable[[ZeroTaxType], ItemMasterSpec]]:
    """Makes an item (with opening stock) in a category of the given zero type; the category goes last."""
    categories = OwnedTaxCategories(guarded_page, run_id)

    def make(zero_type: ZeroTaxType) -> ItemMasterSpec:
        category = categories.saved(zero_type)
        return items.saved_with_opening(items.spec(category), OPENING)

    yield make
    items.delete_unused()
    categories.delete_all()


@pytest.mark.parametrize(
    "zero_type",
    [
        pytest.param(ZeroTaxType.NIL_RATED, id="rows-76-90-nil-rated"),
        pytest.param(ZeroTaxType.EXEMPTED, id="row-91-exempted"),
        pytest.param(ZeroTaxType.ZERO_RATED, id="row-91-zero-rated"),
    ],
)
def test_tax_is_charged_only_on_the_taxable_line(
    guarded_page: Page, zero_tax_item: Callable[[ZeroTaxType], ItemMasterSpec], zero_type: ZeroTaxType
) -> None:
    item = zero_tax_item(zero_type)
    taxable_value = TAXABLE_RATE * QUANTITY
    tax = line_tax(taxable_value, TAXABLE_SLAB, intra_state=True)
    zero_value = item.sale_rate * ZERO_QUANTITY
    sale = GarmentsSalePage(guarded_page)
    sale.open_new_bill()
    sale.choose_party(INTRA_STATE_PARTY)

    sale.add_item(0, TAXABLE_ITEM, QUANTITY)
    sale.add_item(1, item.product, ZERO_QUANTITY)

    totals = BillTotals(guarded_page)
    totals.expect_invoice_value(taxable_value + tax.total_tax + zero_value)
    assert totals.tax_amounts() == {"CGST Output": tax.cgst, "SGST Output": tax.sgst}
    totals.leave_without_saving()
