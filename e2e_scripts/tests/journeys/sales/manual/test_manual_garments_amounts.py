"""Manual cases 24, 75, 76, 89, 90, 95, 100, 101, 103, 174, 176, 213-215, 217, 218 on a garments sale bill.

Safety: nothing is saved. Settings a test changes are put back by its fixture; the tenant is shared, so
every test runs on the chemist-tenant worker. Expected figures come from `test_data.bill_calc`, never from
the screen.
Party Ajay is in the company's state (CGST + SGST); "Sample Item" sells at 100 with GST 5%, quantity 3.
Rules cited, all in newmarg-webangular20/src/app/Component/Transaction/InverntoryTransaction:
- bill discount is taken on quantity x rate minus the item and volume discounts, slab by slab
  (dataCalculation.ts:1242-1320), so an item discount and a bill discount compound;
- a bill discount amount above the goods value is refused with "Bill Discount Amount should be less than or
  equals to Goods Value" and cleared (dataCalculation.ts:1371-1373, global.ts:19332);
- volume discount: Percentage = percent of the line amount, Lumpsum = the value, perUnit = value x quantity
  (dataCalculation.ts:437-480); "Amount Calculation On Billing" 1 = rate x quantity, 2 = minus the item and
  volume discounts (dataCalculation.ts:750-770).
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.exempt_item import EXEMPT_ITEM, ExemptItem
from pages.company_switch_page import GARMENTS_COMPANY
from pages.components.bill_discount import BillDiscount
from pages.components.bill_totals import BillTotals
from pages.sale.manual import messages
from pages.sale.manual.bill_messages import BillMessages
from pages.sale.manual.garments_lines import ManualGarmentsSale
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, HeldOptions
from pages.sale.manual.volume_discount_modes import first_volume_discount_held
from pages.settings.gst_configuration import GstConfiguration
from pages.settings.item_discount_configuration import VolumeDiscountType
from test_data.bill_calc import (
    IntraStateBill,
    compound_discount,
    exclusive_bill,
    inclusive_bill,
    percent_of,
)

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

PARTY = "Ajay"
ITEM = "Sample Item"
OTHER_ITEM = "Barcdoe"
QUANTITY = Decimal(3)
RATE = Decimal(100)
GROSS_VALUE = RATE * QUANTITY
SLAB = Decimal(5)
TEN_PERCENT = Decimal(10)
ABOVE_GOODS_VALUE = Decimal(400)
EXEMPT_QUANTITY = Decimal(1)
EXEMPT_VALUE = EXEMPT_ITEM.sale_rate * EXEMPT_QUANTITY
GARMENTS: Account = "garments"


def expect_bill(totals: BillTotals, expected: IntraStateBill) -> None:
    totals.expect_invoice_value(expected.invoice_value)
    totals.expect_tax_amounts({"CGST Output": expected.cgst, "SGST Output": expected.sgst})


@pytest.fixture
def exempt_item(company_page: Callable[[Account, str], Page]) -> str:
    """The shared 0% GST item, made once on the garments company; it must exist before the bill opens."""
    return ExemptItem(company_page(GARMENTS, GARMENTS_COMPANY)).ensure_exists()


@pytest.fixture
def bill_for_party(manual_sale: ManualGarmentsSale) -> ManualGarmentsSale:
    manual_sale.choose_party(PARTY)
    return manual_sale


@pytest.fixture
def bill_with_item(bill_for_party: ManualGarmentsSale) -> ManualGarmentsSale:
    bill_for_party.add_item(0, ITEM, QUANTITY)
    return bill_for_party


def test_replacing_a_row_item_shows_the_new_item(bill_with_item: ManualGarmentsSale) -> None:
    """Row 24 ("change it to another item"): the row names the new item, not the old one."""
    bill_with_item.replace_item(0, OTHER_ITEM, QUANTITY)

    bill_with_item.expect_item_in_row(0, OTHER_ITEM)


def test_tax_is_charged_only_on_the_taxable_line(
    exempt_item: str, bill_with_item: ManualGarmentsSale, totals: BillTotals
) -> None:
    """Rows 75, 89 (taxable + exempt) and 76, 90 (the 0% item stands for nil-rated; see the scenario file)."""
    bill_with_item.add_plain_item(1, exempt_item, EXEMPT_QUANTITY)

    taxable = exclusive_bill(GROSS_VALUE, SLAB)
    totals.expect_invoice_value(taxable.invoice_value + EXEMPT_VALUE)
    totals.expect_tax_amounts({"CGST Output": taxable.cgst, "SGST Output": taxable.sgst})


def test_an_exempt_item_alone_carries_no_tax(
    exempt_item: str, bill_for_party: ManualGarmentsSale, totals: BillTotals
) -> None:
    """Row 95: "GST should be zero"."""
    bill_for_party.add_plain_item(0, exempt_item, EXEMPT_QUANTITY)

    totals.expect_invoice_value(EXEMPT_VALUE)
    totals.expect_tax_amounts({})


def test_item_and_bill_discount_compound(
    bill_with_item: ManualGarmentsSale, totals: BillTotals, bill_discount_fields: BillDiscount
) -> None:
    """Row 101: the bill discount is taken on the amount left after the item discount."""
    bill_with_item.change_item_discount(0, TEN_PERCENT)

    bill_discount_fields.enter_percent1(TEN_PERCENT)

    taxable = compound_discount(GROSS_VALUE, TEN_PERCENT, TEN_PERCENT)
    expect_bill(totals, exclusive_bill(taxable, SLAB))


def test_bill_discount_above_the_goods_value_is_refused(
    bill_with_item: ManualGarmentsSale, totals: BillTotals, bill_discount_fields: BillDiscount
) -> None:
    """Row 100: the warning shows and the invoice stays as if no discount was typed."""
    bill_discount_fields.enter_amount(ABOVE_GOODS_VALUE)

    BillMessages(bill_with_item.page).expect_warning(messages.BILL_DISCOUNT_ABOVE_GOODS)
    expect_bill(totals, exclusive_bill(GROSS_VALUE, SLAB))


def test_item_discount_follows_a_rate_change(bill_with_item: ManualGarmentsSale, totals: BillTotals) -> None:
    """Row 103: discount 10% on the new rate of 200."""
    new_rate = Decimal(200)
    bill_with_item.change_item_discount(0, TEN_PERCENT)

    bill_with_item.change_rate(0, new_rate)

    gross = new_rate * QUANTITY
    expect_bill(totals, exclusive_bill(gross - percent_of(gross, TEN_PERCENT), SLAB))


@pytest.fixture
def inclusive_item_bill(
    bill_with_item: ManualGarmentsSale, original_gst_type: GstConfiguration
) -> ManualGarmentsSale:
    original_gst_type.select_gst_type("Inclusive")
    return bill_with_item


def test_inclusive_gst_with_an_item_discount(
    inclusive_item_bill: ManualGarmentsSale, totals: BillTotals
) -> None:
    """Row 174. Assumed rule (question in the scenario file): the tax is the share of the payable amount
    left after the discount, payable x slab / (100 + slab)."""
    inclusive_item_bill.change_item_discount(0, TEN_PERCENT)

    payable = GROSS_VALUE - percent_of(GROSS_VALUE, TEN_PERCENT)
    expect_bill(totals, inclusive_bill(payable, SLAB))


def test_inclusive_gst_with_a_bill_discount(
    inclusive_item_bill: ManualGarmentsSale, totals: BillTotals, bill_discount_fields: BillDiscount
) -> None:
    """Row 176, same assumed rule as row 174."""
    bill_discount_fields.enter_percent1(TEN_PERCENT)

    payable = GROSS_VALUE - percent_of(GROSS_VALUE, TEN_PERCENT)
    expect_bill(totals, inclusive_bill(payable, SLAB))


@dataclass(frozen=True)
class VolumeDiscount:
    """What is typed into the first volume discount and the money it takes off 3 x 100."""

    mode: VolumeDiscountType
    typed: Decimal
    taken_off: Decimal


VOLUME_DISCOUNTS = [
    pytest.param(VolumeDiscount("Percentage", Decimal(10), Decimal(30)), id="percentage-10"),
    pytest.param(VolumeDiscount(" Lumpsum ", Decimal(25), Decimal(25)), id="lumpsum-25"),
    pytest.param(VolumeDiscount(" perUnit ", Decimal(5), Decimal(15)), id="per-unit-5-times-3"),
]


@pytest.mark.parametrize("discount", VOLUME_DISCOUNTS)
def test_volume_discount_is_taken_as_the_chosen_mode(
    bill_with_item: ManualGarmentsSale, totals: BillTotals, discount: VolumeDiscount
) -> None:
    """Rows 213 (lumpsum), 214 (percentage) and 215 (per unit)."""
    with first_volume_discount_held(bill_with_item.page, discount.mode):
        bill_with_item.change_first_volume_discount(0, discount.typed)

        expect_bill(totals, exclusive_bill(GROSS_VALUE - discount.taken_off, SLAB))


@dataclass(frozen=True)
class LineAmount:
    """The Amount Calculation On Billing choice and the line amount it shows with a 10% item discount."""

    choice: str
    shown: Decimal


LINE_AMOUNTS = [
    pytest.param(LineAmount("Rate*Qty", GROSS_VALUE), id="rate-times-quantity"),
    pytest.param(
        LineAmount("Rate*Qty-discount", GROSS_VALUE - percent_of(GROSS_VALUE, TEN_PERCENT)),
        id="rate-times-quantity-less-discount",
    ),
]


@pytest.mark.parametrize("amount", LINE_AMOUNTS)
def test_line_amount_follows_the_amount_calculation_setting(
    bill_with_item: ManualGarmentsSale, garments_options: HeldOptions, amount: LineAmount
) -> None:
    """Rows 217 (no discount in the amount) and 218 (discount taken off the amount)."""
    garments_options.hold(AMOUNT_CALCULATION, amount.choice)

    bill_with_item.change_item_discount(0, TEN_PERCENT)

    bill_with_item.expect_line_amount(0, amount.shown)
