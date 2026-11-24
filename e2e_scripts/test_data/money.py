"""Money parsing and rounding. Amounts are always Decimal, never float."""

import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation

TWO_PLACES = Decimal("0.01")
NOISE_CHARACTERS = re.compile(r"[₹,\s]|Rs\.?", re.IGNORECASE)
TRAILING_MINUS = re.compile(r"^(?P<digits>[\d.]+)-$")

__all__ = ["ROUND_HALF_EVEN", "ROUND_HALF_UP", "TWO_PLACES", "AmountParseError", "parse_amount", "to_money"]


class AmountParseError(ValueError):
    def __init__(self, text: str) -> None:
        super().__init__(f'Cannot read an amount from "{text}"')


def parse_amount(text: str) -> Decimal:
    """Reads what the app shows: "₹ 1,234.50", "-2114.000", "(10.00)" or "10.00-"."""
    cleaned = NOISE_CHARACTERS.sub("", text)
    try:
        return Decimal(_with_leading_sign(cleaned))
    except InvalidOperation:
        raise AmountParseError(text) from None


def to_money(value: Decimal, rounding: str = ROUND_HALF_UP) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=rounding)


def _with_leading_sign(cleaned: str) -> str:
    if cleaned.startswith("(") and cleaned.endswith(")"):
        return "-" + cleaned[1:-1]
    trailing = TRAILING_MINUS.match(cleaned)
    return "-" + trailing.group("digits") if trailing else cleaned
