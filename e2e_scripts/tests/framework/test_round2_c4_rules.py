"""Offline checks of the rule helpers of round 2, part C4 (no app needed)."""

from decimal import Decimal

import pytest

from pages.sale.round2_c4.round_off import RoundOff, invoice_after_round_off

pytestmark = pytest.mark.framework


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (RoundOff.NO, Decimal("108.27")),
        (RoundOff.AUTO, Decimal(108)),
        (RoundOff.UPPER, Decimal(109)),
        (RoundOff.LOWER, Decimal(108)),
    ],
)
def test_round_off_modes_on_108_27(mode: RoundOff, expected: Decimal) -> None:
    assert invoice_after_round_off(Decimal("108.27"), mode) == expected


def test_auto_rounds_half_up() -> None:
    assert invoice_after_round_off(Decimal("261.50"), RoundOff.AUTO) == Decimal(262)
