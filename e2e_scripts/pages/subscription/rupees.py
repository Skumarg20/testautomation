"""Rupee amounts as the subscription screens print them: "₹ 29,700", "₹ 5400/-", "₹.30", "1,89,248.40"."""

from decimal import Decimal

PRINTED_DECORATIONS = ("₹", ",", "/-")


def rupees_in(text: str) -> Decimal:
    digits = text
    for decoration in PRINTED_DECORATIONS:
        digits = digits.replace(decoration, "")
    return Decimal(digits.strip())
