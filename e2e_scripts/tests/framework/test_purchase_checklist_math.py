"""Offline checks of the purchase-line arithmetic taken from the Angular source (no app needed)."""

from decimal import Decimal

import pytest

from pages.purchase.checklist.line_math import (
    base_quantity,
    cost_of,
    item_discounts,
    percentage_volume_discount,
    split_quantity,
)

pytestmark = pytest.mark.framework


def test_second_item_discount_is_taken_on_what_the_first_left() -> None:
    discounts = item_discounts(Decimal(1000), (Decimal(10), Decimal(5)))

    assert discounts.discount1 == Decimal("100.00")
    assert discounts.discount2 == Decimal("45.00")
    assert discounts.total == Decimal("145.00")


def test_item_discount_without_a_second_discount_is_the_first_only() -> None:
    assert item_discounts(Decimal(1000), (Decimal(20), Decimal(0))).total == Decimal("200.00")


def test_percentage_volume_discount_is_a_share_of_the_amount() -> None:
    assert percentage_volume_discount(Decimal(1000), Decimal(3)) == Decimal("30.00")


def test_cost_with_the_free_pieces_shared_over_all_pieces() -> None:
    cost = cost_of(Decimal(100), (Decimal(100), Decimal(50)), Decimal(0))

    assert cost.with_deal == Decimal("66.67")
    assert cost.without_deal == Decimal("100.00")


def test_cost_after_a_discount() -> None:
    cost = cost_of(Decimal(100), (Decimal(10), Decimal(0)), Decimal(100))

    assert cost.with_deal == cost.without_deal == Decimal("90.00")


def test_one_bigger_unit_and_five_pieces_of_ten_per_unit_are_fifteen() -> None:
    assert base_quantity(1, 5, 10) == 15


def test_stored_quantity_splits_back_into_bigger_and_smaller_units() -> None:
    assert split_quantity(15, 10) == (1, 5)
