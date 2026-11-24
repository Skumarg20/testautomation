"""Free-deal, lot-rate, scheme and additional-charge arithmetic, written from the Angular source.

Item-master deal "Free + Scheme" (scheme1 + scheme2), Scheme.businesslogic.ts:716-780:
  Full Scheme  free = floor(quantity / scheme1) * scheme2                     (:723-726)
  Half Scheme  0 below scheme1 / 2, else quantity * scheme2 / scheme1          (:727-737,
  dataCalculation.ts:2499-2504)
  Whole Scheme floor(quantity / scheme1) * scheme2 (reduced by the common factor, processout:13599-13608)
Net Scheme (Common.service.ts:2386-2412, formula 1 = 0.09 x quantity, 2 = 0.10 x quantity), Whole scheme
(:768-778): free = int(whole free) + net(quantity mod (scheme1 / scheme2)).
Lot rate (lotRate.component.ts:206-216): percentage -> rate / (100 + p) x 100; rate -> rate / (qty +
free) x qty.
Additional charge (dataCalculation.ts:872-880, 959-971): percentage -> (goods - bill discount) x p / 100;
GST on a taxable charge is amount x rate / 100 (:837-846).
Multi unit (processout.transaction.component.ts:13846-13849): quantity = unit2 x conversion + unit1.
"""

from decimal import ROUND_HALF_UP, Decimal

HUNDRED = Decimal(100)
TWO_PLACES = Decimal("0.01")
NET_SHARE_BY_FORMULA = {1: Decimal("0.09"), 2: Decimal("0.10"), 3: Decimal("0.09"), 4: Decimal("0.10")}


def money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def full_scheme_free(quantity: int, deal: tuple[int, int]) -> int:
    buy, free = deal
    return (quantity // buy) * free


def half_scheme_free(quantity: int, deal: tuple[int, int]) -> Decimal:
    buy, free = deal
    if Decimal(quantity) < Decimal(buy) / 2:
        return Decimal(0)
    return Decimal(quantity) * free / buy


def net_free(quantity: Decimal, formula: int) -> Decimal:
    return money(NET_SHARE_BY_FORMULA[formula] * quantity)


def whole_scheme_net_free(quantity: int, deal: tuple[int, int], formula: int) -> Decimal:
    buy, free = deal
    leftover = Decimal(quantity) % (Decimal(buy) / free)
    return money(Decimal(full_scheme_free(quantity, deal)) + net_free(leftover, formula))


def lot_rate_by_percentage(rate: Decimal, percentage: Decimal) -> Decimal:
    return money(rate / (HUNDRED + percentage) * HUNDRED)


def lot_rate_by_deal(rate: Decimal, deal: tuple[int, int]) -> Decimal:
    quantity, free = deal
    return money(rate / (quantity + free) * quantity)


def charge_by_percentage(goods: Decimal, bill_discount: Decimal, percentage: Decimal) -> Decimal:
    return money((goods - bill_discount) * percentage / HUNDRED)


def charge_tax(charge: Decimal, rate: Decimal) -> Decimal:
    return money(charge * rate / HUNDRED)


def base_quantity(bigger_units: int, smaller_units: int, pieces_per_bigger_unit: int) -> int:
    return bigger_units * pieces_per_bigger_unit + smaller_units


def multi_unit_amount(quantity: int, rate_per_piece: Decimal) -> Decimal:
    return money(quantity * rate_per_piece)


def volume_discount(mode: str, value: Decimal, line: tuple[int, Decimal]) -> Decimal:
    """Modes of dataCalculation.ts:443-486: perUnit, Lumpsum, Percentage, No. `line` is (quantity, amount)."""
    quantity, amount = line
    shares = {
        "perUnit": value * quantity,
        "Lumpsum": value,
        "Percentage": amount * value / HUNDRED,
        "No": Decimal(0),
    }
    return money(shares[mode])


def reverse_free(quantity: int, deal: tuple[int, int]) -> Decimal:
    """Reverse Calculation with Net Scheme (Scheme.businesslogic.ts:793-805): free = quantity / buy x free."""
    buy, free = deal
    return Decimal(quantity) / buy * free


def all_scheme_free(quantity: int, deal: tuple[int, int]) -> Decimal:
    """All Scheme above one piece (:760-766): the proportional share, quantity x free / buy."""
    buy, free = deal
    return Decimal(quantity) * free / buy
