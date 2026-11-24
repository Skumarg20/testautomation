"""Independent expected-tax calculator, so tests never take the app's own numbers as truth."""

from dataclasses import dataclass
from decimal import Decimal

from test_data.money import ROUND_HALF_UP, to_money

GST_SLABS: frozenset[Decimal] = frozenset(Decimal(rate) for rate in (0, 5, 12, 18, 28, 40))
# decision D5 pending: how the app rounds tax (per line or per bill, half-up or half-even) is not yet agreed
DEFAULT_ROUNDING = ROUND_HALF_UP
HUNDRED = Decimal(100)
TWO = Decimal(2)
ZERO = Decimal(0)


class UnsupportedGstRateError(ValueError):
    def __init__(self, rate: Decimal) -> None:
        super().__init__(f"{rate}% is not a GST slab; expected one of {sorted(GST_SLABS)}")


@dataclass(frozen=True)
class TaxBreakup:
    cgst: Decimal
    sgst: Decimal
    igst: Decimal

    @property
    def total_tax(self) -> Decimal:
        return self.cgst + self.sgst + self.igst


class GstCalculator:
    """Expected tax for a taxable value, with the rounding mode chosen once at construction."""

    def __init__(self, rounding: str = DEFAULT_ROUNDING) -> None:
        self._rounding = rounding

    def line_tax(self, base: Decimal, rate: Decimal, intra_state: bool) -> TaxBreakup:
        """Intra-state splits half CGST and half SGST; inter-state is all IGST."""
        if rate not in GST_SLABS:
            raise UnsupportedGstRateError(rate)
        tax = base * rate / HUNDRED
        if intra_state:
            half = to_money(tax / TWO, self._rounding)
            return TaxBreakup(cgst=half, sgst=half, igst=ZERO)
        return TaxBreakup(cgst=ZERO, sgst=ZERO, igst=to_money(tax, self._rounding))


def line_tax(base: Decimal, rate: Decimal, intra_state: bool) -> TaxBreakup:
    return GstCalculator().line_tax(base, rate, intra_state)
