"""J05 garments purchase bill: GST split and bill value against independent expected values.

Nothing is saved. Lines are entered on the open purchase screen (Alt+P), the input tax and total shown are
compared with values worked out here, and the screen is closed without saving. Suppliers: Namrata is
registered in another state; the intra-state registered and the composition suppliers are made by the test.
The app rounds each tax line to three decimals, half up (CommonFunction.roundoffvalue).
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest

from pages.components.bill_totals import BillTotals
from pages.purchase.documents import messages
from pages.purchase.garments.purchase_bill_page import GarmentsPurchaseLine, PurchaseBillPage
from test_data.gst_calc import line_tax

# Reads the garments GST type that test_sales_gst_discount.py changes tenant-wide, so it runs on the same
# worker as that writer.
pytestmark = [pytest.mark.p0, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("chemist-tenant")]

INVOICE_NUMBER = "778899"
UNREGISTERED_SUPPLIER = "Mayur Sharma"
INTER_STATE_SUPPLIER = "Namrata"
THREE_PLACES = Decimal("0.001")
HUNDRED = Decimal(100)
SAMPLE_ITEM_SLAB = Decimal(5)
BARCDOE_SLAB = Decimal(28)


def _enter_line(page: PurchaseBillPage, supplier: str, line: GarmentsPurchaseLine) -> None:
    page.choose_supplier(supplier)
    page.start_manual_entry()
    page.enter_invoice_number_and_date(INVOICE_NUMBER)
    page.add_garments_line(0, line)


def _half_up(value: Decimal) -> Decimal:
    return value.quantize(THREE_PLACES, rounding=ROUND_HALF_UP)


def test_intra_state_purchase_splits_input_tax_into_cgst_and_sgst(
    intra_state_supplier: str, purchase_page: PurchaseBillPage, totals: BillTotals
) -> None:
    line = GarmentsPurchaseLine("Sample Item", Decimal(10), Decimal(100))
    taxable_value = line.quantity * line.rate
    tax = line_tax(taxable_value, SAMPLE_ITEM_SLAB, intra_state=True)

    _enter_line(purchase_page, intra_state_supplier, line)

    totals.expect_invoice_value(taxable_value + tax.total_tax)
    assert totals.tax_amounts() == {"CGST Input": tax.cgst, "SGST Input": tax.sgst}


def test_inter_state_purchase_charges_igst_only(purchase_page: PurchaseBillPage, totals: BillTotals) -> None:
    line = GarmentsPurchaseLine("Barcdoe", Decimal(3), Decimal(50))
    taxable_value = line.quantity * line.rate
    tax = line_tax(taxable_value, BARCDOE_SLAB, intra_state=False)

    _enter_line(purchase_page, INTER_STATE_SUPPLIER, line)

    totals.expect_invoice_value(taxable_value + tax.total_tax)
    assert totals.tax_amounts() == {"IGST Input": tax.igst}


def test_odd_paise_tax_is_rounded_half_up_on_each_tax_line(
    intra_state_supplier: str, purchase_page: PurchaseBillPage, totals: BillTotals
) -> None:
    """25.30 at 5% is 1.265 of tax; each half is 0.6325, which half up makes 0.633 (half even: 0.632)."""
    line = GarmentsPurchaseLine("Sample Item", Decimal(1), Decimal("25.3"))
    half_of_tax = _half_up(line.quantity * line.rate * SAMPLE_ITEM_SLAB / HUNDRED / 2)

    _enter_line(purchase_page, intra_state_supplier, line)

    totals.expect_tax_amounts({"CGST Input": half_of_tax, "SGST Input": half_of_tax})


def test_unregistered_supplier_is_flagged_on_selection(purchase_page: PurchaseBillPage) -> None:
    purchase_page.choose_supplier(UNREGISTERED_SUPPLIER)

    purchase_page.expect_toast(messages.UNREGISTERED_SUPPLIER)


def test_unregistered_supplier_carries_no_input_tax(
    purchase_page: PurchaseBillPage, totals: BillTotals
) -> None:
    line = GarmentsPurchaseLine("Sample Item", Decimal(10), Decimal(100))

    _enter_line(purchase_page, UNREGISTERED_SUPPLIER, line)

    assert totals.tax_amounts() == {}
    totals.expect_invoice_value(line.quantity * line.rate)


def test_composition_supplier_is_flagged_and_carries_no_input_tax(
    composition_supplier: str, purchase_page: PurchaseBillPage, totals: BillTotals
) -> None:
    line = GarmentsPurchaseLine("Sample Item", Decimal(10), Decimal(100))

    purchase_page.choose_supplier(composition_supplier)
    purchase_page.expect_toast(messages.COMPOSITION_SUPPLIER)
    purchase_page.start_manual_entry()
    purchase_page.enter_invoice_number_and_date(INVOICE_NUMBER)
    purchase_page.add_garments_line(0, line)

    assert totals.tax_amounts() == {}
