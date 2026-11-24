"""Arithmetic of one purchase line, written from the Angular source (no screen reading).

Item discounts: `calaculateDiscount` (Component/Transaction/InverntoryTransaction/dataCalculation.ts:419-440).
  discount 1 = (amount - scheme - volume discounts) x discount1% / 100
  discount 2 = (amount - scheme - volume discounts - discount 1) x discount2% / 100
Volume discount, "Percentage" mode (:458-460, :481-483): (amount - scheme) x volume% / 100; "Lump sum" mode
(:452-453, :476-477): the typed value; "Per unit" mode (:447-448, :471-472): value x quantity.
Two-unit quantity: `updateBothUnitQty` (Services/Helper.services.ts:10558-10566) shows quantity as
floor(quantity / ratio) : quantity mod ratio; the sheet's row "1 * 10 + 5" is the reverse.
Cost: `calcMargin` (transactioninbatch.component.ts:235-237): (rate x quantity - discounts) divided by
(quantity + free) "with deal" and by quantity "without deal", both shown to 2 places.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

HUNDRED = Decimal(100)
TWO_PLACES = Decimal("0.01")
ZERO = Decimal(0)


@dataclass(frozen=True)
class ItemDiscounts:
    discount1: Decimal
    discount2: Decimal

    @property
    def total(self) -> Decimal:
        return self.discount1 + self.discount2


@dataclass(frozen=True)
class Cost:
    with_deal: Decimal
    without_deal: Decimal


def item_discounts(amount: Decimal, percentages: tuple[Decimal, Decimal]) -> ItemDiscounts:
    """Both item discounts of a line without scheme or volume discount; `percentages` is (discount 1, 2)."""
    first_percentage, second_percentage = percentages
    first = _money(amount * first_percentage / HUNDRED)
    second = _money((amount - first) * second_percentage / HUNDRED)
    return ItemDiscounts(first, second)


def percentage_volume_discount(amount: Decimal, percentage: Decimal) -> Decimal:
    return _money(amount * percentage / HUNDRED)


def cost_of(rate: Decimal, quantities: tuple[Decimal, Decimal], discounts: Decimal) -> Cost:
    """`quantities` is (paid quantity, free quantity)."""
    quantity, free = quantities
    paid_value = rate * quantity - discounts
    return Cost(_money(paid_value / (quantity + free)), _money(paid_value / quantity))


def base_quantity(bigger_units: int, smaller_units: int, pieces_per_bigger_unit: int) -> int:
    """What the back end holds for "unit 2 = 1, unit 1 = 5" at 1 x 10: 1 * 10 + 5."""
    return bigger_units * pieces_per_bigger_unit + smaller_units


def split_quantity(quantity: int, pieces_per_bigger_unit: int) -> tuple[int, int]:
    """(bigger units, smaller units) the app shows for a stored quantity."""
    return quantity // pieces_per_bigger_unit, quantity % pieces_per_bigger_unit


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
