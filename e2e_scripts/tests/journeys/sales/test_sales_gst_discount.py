"""Manual cases AJ-013..AJ-018: GST calculation type and discounts on a garments sale bill.

Safety: nothing is saved. Settings changed by a test are restored by its fixture; the tenant is shared,
so every test runs on the chemist-tenant worker.
Expected figures come from `test_data.bill_calc`, never from the screen.
"""

from decimal import Decimal

import pytest

from pages.components.bill_discount import BillDiscount
from pages.components.bill_totals import BillTotals
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.settings.gst_configuration import GstConfiguration
from test_data.bill_calc import (
    IntraStateBill,
    compound_discount,
    exclusive_bill,
    inclusive_bill,
    percent_of,
    rounded_to_rupee,
)

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

INTRA_STATE_PARTY = "Ajay"
ITEM = "Sample Item"
QUANTITY = Decimal(3)
GROSS_VALUE = Decimal(100) * QUANTITY
SLAB = Decimal(5)
DISCOUNT_PERCENT = Decimal(10)
DISCOUNT_AMOUNT = Decimal(45)
ZERO = Decimal(0)


@pytest.fixture
def bill_with_item(sale_page: GarmentsSalePage) -> GarmentsSalePage:
    sale_page.choose_party(INTRA_STATE_PARTY)
    sale_page.add_item(0, ITEM, QUANTITY)
    return sale_page


def expect_bill(totals: BillTotals, expected: IntraStateBill) -> None:
    totals.expect_invoice_value(expected.invoice_value)
    totals.expect_tax_amounts({"CGST Output": expected.cgst, "SGST Output": expected.sgst})


def test_aj013_item_discount_is_taken_off_before_tax(
    bill_with_item: GarmentsSalePage, totals: BillTotals
) -> None:
    taxable = GROSS_VALUE - percent_of(GROSS_VALUE, DISCOUNT_PERCENT)

    bill_with_item.change_item_discount(0, DISCOUNT_PERCENT)

    expect_bill(totals, exclusive_bill(taxable, SLAB))


def test_aj014_inclusive_calculation_finds_the_tax_inside_the_amount(
    bill_with_item: GarmentsSalePage, totals: BillTotals, original_gst_type: GstConfiguration
) -> None:
    original_gst_type.select_gst_type("Inclusive")

    expect_bill(totals, inclusive_bill(GROSS_VALUE, SLAB))


def test_aj015_exclusive_calculation_adds_the_tax_on_top(
    bill_with_item: GarmentsSalePage, totals: BillTotals, original_gst_type: GstConfiguration
) -> None:
    original_gst_type.select_gst_type("Exclusive")

    expect_bill(totals, exclusive_bill(GROSS_VALUE, SLAB))


def test_aj016_bill_discount_percent_1_is_taken_off_before_tax(
    bill_with_item: GarmentsSalePage, totals: BillTotals, bill_discount_fields: BillDiscount
) -> None:
    taxable = GROSS_VALUE - percent_of(GROSS_VALUE, DISCOUNT_PERCENT)

    bill_discount_fields.enter_percent1(DISCOUNT_PERCENT)

    expect_bill(totals, exclusive_bill(taxable, SLAB))


def test_aj017_bill_discount_percent_2_is_taken_off_before_tax(
    bill_with_item: GarmentsSalePage, totals: BillTotals, bill_discount_fields: BillDiscount
) -> None:
    taxable = GROSS_VALUE - percent_of(GROSS_VALUE, DISCOUNT_PERCENT)

    bill_discount_fields.enter_percent2(DISCOUNT_PERCENT)

    expect_bill(totals, exclusive_bill(taxable, SLAB))


def test_aj018_bill_discount_amount_is_taken_off_before_tax(
    bill_with_item: GarmentsSalePage, totals: BillTotals, bill_discount_fields: BillDiscount
) -> None:
    bill_discount_fields.enter_amount(DISCOUNT_AMOUNT)

    expect_bill(totals, exclusive_bill(GROSS_VALUE - DISCOUNT_AMOUNT, SLAB))


def test_aj016_017_bill_discounts_1_and_2_compound(
    bill_with_item: GarmentsSalePage, totals: BillTotals, bill_discount_fields: BillDiscount
) -> None:
    taxable = compound_discount(GROSS_VALUE, DISCOUNT_PERCENT, DISCOUNT_PERCENT)

    bill_discount_fields.enter_percent1(DISCOUNT_PERCENT)
    expect_bill(totals, exclusive_bill(compound_discount(GROSS_VALUE, DISCOUNT_PERCENT, ZERO), SLAB))
    bill_discount_fields.enter_percent2(DISCOUNT_PERCENT)

    expect_bill(totals, exclusive_bill(taxable, SLAB))


@pytest.mark.parametrize(
    "discount_amount",
    [
        pytest.param(Decimal(47), id="265.650-rounds-up-to-266"),
        pytest.param(Decimal(51), id="261.450-rounds-down-to-261"),
    ],
)
@pytest.mark.usefixtures("bill_with_item")
def test_invoice_value_is_rounded_to_the_nearest_rupee(
    totals: BillTotals, bill_discount_fields: BillDiscount, discount_amount: Decimal
) -> None:
    unrounded = exclusive_bill(GROSS_VALUE - discount_amount, SLAB).invoice_value

    bill_discount_fields.enter_amount(discount_amount)

    totals.expect_invoice_value(rounded_to_rupee(unrounded))
