"""J40 Conversion: One to Many and Many to One, read from the main-store stock of this run's items.

BIG has Conversion 1 and opening 80; S1 has Conversion 1 and S5 Conversion 5 (pack MF-29).
"""

from collections.abc import Callable

import pytest

from pages.stock.item_stock_balance import ItemStockBalance
from test_data.manufacturing import ConversionEntry, ConversionItems, many_to_one, one_to_many

# The fixtures switch a tenant-wide Control Room option on and back (spec N1).
pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

Convert = Callable[[ConversionEntry], str]


def test_one_to_many_takes_the_converted_quantity_off_the_big_item(
    conversion_items: ConversionItems, convert: Convert, conversion_stock: ItemStockBalance
) -> None:
    """MF-30: S1 x 5 and S5 x 5 take 30 off BIG: 80 -> 50."""
    entry = one_to_many(conversion_items)
    convert(entry)
    assert conversion_stock.main_store_stock(entry.big.product) == entry.big.opening - entry.big_item_quantity


def test_one_to_many_adds_the_small_items(
    conversion_items: ConversionItems, convert: Convert, conversion_stock: ItemStockBalance
) -> None:
    """MF-30: S1 +5 and S5 +5."""
    entry = one_to_many(conversion_items)
    convert(entry)
    for line in entry.lines:
        assert conversion_stock.main_store_stock(line.item.product) == line.item.opening + line.quantity


def test_many_to_one_adds_the_converted_quantity_to_the_big_item(
    conversion_items: ConversionItems, convert: Convert, conversion_stock: ItemStockBalance
) -> None:
    """MF-31: S1 x 5 and S5 x 1 add 10 to BIG, posted exactly once (MB-038393): 80 -> 90."""
    entry = many_to_one(conversion_items)
    convert(entry)
    assert conversion_stock.main_store_stock(entry.big.product) == entry.big.opening + entry.big_item_quantity


def test_many_to_one_takes_the_small_items_off(
    conversion_items: ConversionItems, convert: Convert, conversion_stock: ItemStockBalance
) -> None:
    """MF-31: S1 -5 and S5 -1."""
    entry = many_to_one(conversion_items)
    convert(entry)
    for line in entry.lines:
        assert conversion_stock.main_store_stock(line.item.product) == line.item.opening - line.quantity
