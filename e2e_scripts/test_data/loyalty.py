"""Loyalty earning rules for the CRM loyalty tests (specs/crm-module.md, LY cases)."""

from dataclasses import dataclass

# Points per bill amount stay small whole numbers, like the setup the probe saved (Rs. 100 earns 7 points).
LOWEST_TEST_POINTS = 10
TEST_POINTS_SPAN = 80
HEX_BASE = 16


@dataclass(frozen=True)
class LoyaltyEarning:
    """'Rs.' of bill amount that earns 'Point' points; kept as the text the form shows."""

    amount: str
    points: str


def earning_unlike(current: LoyaltyEarning, run_id: str) -> LoyaltyEarning:
    """The same amount with a run-specific number of points that differs from the current one."""
    points = LOWEST_TEST_POINTS + int(run_id, HEX_BASE) % TEST_POINTS_SPAN
    if str(points) == current.points:
        points += 1
    return LoyaltyEarning(current.amount, str(points))
