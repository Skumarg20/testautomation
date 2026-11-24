"""Independent expected bill figures at the 3 decimals the app shows (rounding rule D5 still pending)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

THREE_PLACES = Decimal("0.001")
HUNDRED = Decimal(100)
TWO = Decimal(2)


@dataclass(frozen=True)
class IntraStateBill:
    cgst: Decimal
    sgst: Decimal
    invoice_value: Decimal


def percent_of(base: Decimal, percent: Decimal) -> Decimal:
    return base * percent / HUNDRED


def rounded_to_rupee(invoice_value: Decimal) -> Decimal:
    """Product-owner rule: nearest whole rupee; exactly .50 rounds up (unconfirmed)."""
    return invoice_value.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def compound_discount(gross: Decimal, first_percent: Decimal, second_percent: Decimal) -> Decimal:
    """Product-owner rule: discount 1 first, then discount 2 on the reduced total."""
    after_first = gross - percent_of(gross, first_percent)
    return after_first - percent_of(after_first, second_percent)


def exclusive_bill(taxable_value: Decimal, slab: Decimal) -> IntraStateBill:
    """Tax is added on top of the taxable value."""
    half_tax = _three_places(percent_of(taxable_value, slab) / TWO)
    return IntraStateBill(half_tax, half_tax, taxable_value + 2 * half_tax)


def inclusive_bill(payable: Decimal, slab: Decimal) -> IntraStateBill:
    """The payable amount already contains the tax: tax = payable * slab / (100 + slab)."""
    half_tax = _three_places(payable * slab / (HUNDRED + slab) / TWO)
    return IntraStateBill(half_tax, half_tax, payable)


def _three_places(value: Decimal) -> Decimal:
    return value.quantize(THREE_PLACES, rounding=ROUND_HALF_UP)
