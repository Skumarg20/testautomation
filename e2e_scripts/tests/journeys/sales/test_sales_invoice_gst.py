"""J04 garments sale invoice: GST split and totals against independent expected values.

Safety: nothing is saved. Lines are entered on the open bill screen, the on-screen tax and total are
compared with `test_data.gst_calc`, and the screen is closed without saving (open question Q1).
"""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from pages.components.bill_totals import BillTotals
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from test_data.gst_calc import TaxBreakup, line_tax

# Reads the garments GST type and bill-discount switches that test_sales_gst_discount.py changes tenant-wide,
# so it runs on the same worker as those writers.
pytestmark = [
    pytest.mark.p0,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

INTRA_STATE_PARTY = "Ajay"
INTER_STATE_PARTY = "Arun Sharma"
QUANTITY = Decimal(3)


@dataclass(frozen=True)
class Product:
    name: str
    rate: Decimal
    slab: Decimal

    @property
    def taxable_value(self) -> Decimal:
        return self.rate * QUANTITY


SAMPLE_ITEM = Product("Sample Item", Decimal(100), Decimal(5))
BARCDOE = Product("Barcdoe", Decimal(200), Decimal(28))


@dataclass(frozen=True)
class BillCase:
    party: str
    intra_state: bool
    product: Product

    def expected_tax_rows(self, tax: TaxBreakup) -> dict[str, Decimal]:
        if self.intra_state:
            return {"CGST Output": tax.cgst, "SGST Output": tax.sgst}
        return {"IGST Output": tax.igst}


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(BillCase(INTRA_STATE_PARTY, True, SAMPLE_ITEM), id="SI-01-intra-5pct"),
        pytest.param(BillCase(INTER_STATE_PARTY, False, SAMPLE_ITEM), id="SI-02-inter-5pct"),
        pytest.param(BillCase(INTRA_STATE_PARTY, True, BARCDOE), id="SI-03-intra-28pct"),
        pytest.param(BillCase(INTER_STATE_PARTY, False, BARCDOE), id="SI-04-inter-28pct"),
    ],
)
def test_single_line_splits_gst_by_party_state_and_totals_to_invoice_value(
    sale_page: GarmentsSalePage, totals: BillTotals, case: BillCase
) -> None:
    product = case.product
    tax = line_tax(product.taxable_value, product.slab, case.intra_state)

    sale_page.choose_party(case.party)
    sale_page.add_item(0, product.name, QUANTITY)

    totals.expect_invoice_value(product.taxable_value + tax.total_tax)
    assert sale_page.line_amount(0) == product.taxable_value
    assert totals.tax_amounts() == case.expected_tax_rows(tax)


def test_two_slabs_on_one_intra_state_bill_add_up(sale_page: GarmentsSalePage, totals: BillTotals) -> None:
    products = (SAMPLE_ITEM, BARCDOE)
    taxes = [line_tax(product.taxable_value, product.slab, intra_state=True) for product in products]
    expected_cgst = sum((tax.cgst for tax in taxes), Decimal(0))
    bases = sum((product.taxable_value for product in products), Decimal(0))
    expected_total = bases + sum((tax.total_tax for tax in taxes), Decimal(0))

    sale_page.choose_party(INTRA_STATE_PARTY)
    for row, product in enumerate(products):
        sale_page.add_item(row, product.name, QUANTITY)

    totals.expect_invoice_value(expected_total)
    assert totals.tax_amounts() == {"CGST Output": expected_cgst, "SGST Output": expected_cgst}


def test_unknown_barcode_raises_an_alert(sale_page: GarmentsSalePage) -> None:
    sale_page.choose_party(INTRA_STATE_PARTY)

    sale_page.enter_barcode(0, "99999999")

    sale_page.expect_alert("Barcode Not Available")
    sale_page.dismiss_alert()


def test_odd_rate_taxes_each_half_to_three_decimals_on_screen(
    sale_page: GarmentsSalePage, totals: BillTotals
) -> None:
    odd_rate = Decimal("33.33")
    exact_half = odd_rate * SAMPLE_ITEM.slab / 100 / 2
    sale_page.choose_party(INTRA_STATE_PARTY)
    sale_page.add_item(0, SAMPLE_ITEM.name, Decimal(1))

    sale_page.change_rate(0, odd_rate)

    expected_half = exact_half.quantize(Decimal("0.001"))
    sale_page.expect_line_amount(0, odd_rate)
    totals.expect_tax_amounts({"CGST Output": expected_half, "SGST Output": expected_half})
