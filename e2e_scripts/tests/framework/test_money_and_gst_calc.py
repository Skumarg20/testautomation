"""Offline checks of money parsing and the independent GST calculator."""

from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

import pytest

from test_data.factory import SLAB_RATES, DataFactory
from test_data.gst_calc import GST_SLABS, GstCalculator, TaxBreakup, UnsupportedGstRateError, line_tax
from test_data.models import HOME_STATE_CODE, PurchaseBillSpec
from test_data.money import AmountParseError, parse_amount, to_money

pytestmark = pytest.mark.framework

BASE = Decimal("1000.00")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,234.50", "1234.50"),
        ("₹ 1,234.50", "1234.50"),
        ("₹0.000", "0.000"),
        ("-2114.000", "-2114.000"),
        ("₹ -261890.000", "-261890.000"),
        ("  12  ", "12"),
        ("(10.00)", "-10.00"),
        ("10.00-", "-10.00"),
        ("1,00,000.000", "100000.000"),
    ],
)
def test_parse_amount_reads_what_the_app_shows(text: str, expected: str) -> None:
    assert parse_amount(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "abc", "₹"])
def test_parse_amount_rejects_text_without_a_number(text: str) -> None:
    with pytest.raises(AmountParseError):
        parse_amount(text)


def test_to_money_rounds_half_up_by_default() -> None:
    assert to_money(Decimal("0.125")) == Decimal("0.13")


def test_to_money_can_round_half_even() -> None:
    assert to_money(Decimal("0.125"), ROUND_HALF_EVEN) == Decimal("0.12")


@pytest.mark.parametrize("rate", sorted(GST_SLABS))
def test_intra_state_tax_splits_in_half_between_cgst_and_sgst(rate: Decimal) -> None:
    tax = line_tax(BASE, rate, intra_state=True)

    assert tax.cgst == tax.sgst == BASE * rate / 200
    assert tax.igst == 0
    assert tax.total_tax == BASE * rate / 100


@pytest.mark.parametrize("rate", sorted(GST_SLABS))
def test_inter_state_tax_is_all_igst(rate: Decimal) -> None:
    tax = line_tax(BASE, rate, intra_state=False)

    assert tax == TaxBreakup(cgst=Decimal(0), sgst=Decimal(0), igst=BASE * rate / 100)


def test_intra_state_half_is_rounded_to_paise() -> None:
    assert line_tax(Decimal("33.33"), Decimal(5), intra_state=True).cgst == Decimal("0.83")


def test_rounding_mode_is_chosen_per_calculator() -> None:
    half_up = GstCalculator(ROUND_HALF_UP).line_tax(Decimal("0.50"), Decimal(5), intra_state=False)
    half_even = GstCalculator(ROUND_HALF_EVEN).line_tax(Decimal("0.50"), Decimal(5), intra_state=False)

    assert (half_up.igst, half_even.igst) == (Decimal("0.03"), Decimal("0.02"))


@pytest.mark.parametrize("rate", [Decimal(3), Decimal("7.5"), Decimal(-5)])
def test_a_rate_outside_the_slabs_is_rejected(rate: Decimal) -> None:
    with pytest.raises(UnsupportedGstRateError):
        line_tax(BASE, rate, intra_state=True)


def test_zero_rate_has_no_tax() -> None:
    assert line_tax(BASE, Decimal(0), intra_state=True).total_tax == 0


def test_slabs_are_the_current_gst_rates() -> None:
    assert {Decimal(rate) for rate in (0, 5, 12, 18, 28, 40)} == GST_SLABS


def test_factory_makes_one_item_per_classic_slab_with_decimal_prices() -> None:
    items = DataFactory("r1").items_per_slab()

    assert [item.gst_rate for item in items] == list(SLAB_RATES) == [0, 5, 12, 18, 28]
    assert all(isinstance(item.price, Decimal) for item in items)


def test_factory_party_kinds_differ_in_state_and_registration() -> None:
    data = DataFactory("r1")

    assert data.intra_state_party().intra_state
    assert data.intra_state_party().state_code == HOME_STATE_CODE
    assert not data.inter_state_party().intra_state
    assert data.inter_state_party().registered
    assert not data.unregistered_party().registered


def test_factory_invalid_gstin_party_differs_from_a_valid_one_only_in_the_check_character() -> None:
    data = DataFactory("r1")

    assert data.party_with_invalid_gstin().gstin != data.valid_gstin(HOME_STATE_CODE)
    assert (data.party_with_invalid_gstin().gstin or "")[:-1] == data.valid_gstin(HOME_STATE_CODE)[:-1]


def test_purchase_bill_spec_totals_its_taxable_value_in_decimal() -> None:
    data = DataFactory("r1")
    bill: PurchaseBillSpec = data.purchase_bill(data.intra_state_party(), data.items_per_slab())

    assert bill.taxable_value == Decimal("500.00")
    assert bill.invoice_number == "INV-r1"
