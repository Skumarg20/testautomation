"""J40 Conversion beyond the stock figures: the Item Ledger order on a day with a purchase and a One to Many
(MF-32, MB-034805) and the item's Conversion once it has a conversion entry (MF-33)."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from pages.manufacturing.item_ledger import ItemLedger
from pages.manufacturing.items import expect_conversion_locked, open_item_for_change
from test_data.manufacturing import ConversionEntry, ConversionItems, SameDayEntries, one_to_many

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

Convert = Callable[[ConversionEntry], str]


def test_item_ledger_lists_the_earlier_purchase_before_the_one_to_many(
    one_to_many_after_purchase: SameDayEntries, conversion_page: Page
) -> None:
    """MF-32 / MB-034805: the purchase saved first comes first in BIG's register."""
    entries = one_to_many_after_purchase
    ledger = ItemLedger(conversion_page)
    ledger.open_for(entries.big_product)
    assert ledger.position_of(entries.purchase_number) < ledger.position_of(entries.conversion_number)


def test_item_ledger_running_balance_never_goes_negative(
    one_to_many_after_purchase: SameDayEntries, conversion_page: Page
) -> None:
    """MF-32 / MB-034805: BIG 80 + 10 - 30 never dips below zero on the way."""
    ledger = ItemLedger(conversion_page)
    ledger.open_for(one_to_many_after_purchase.big_product)
    assert ledger.negative_running_balances() == []


def test_conversion_of_an_item_with_a_conversion_entry_cannot_be_changed(
    conversion_items: ConversionItems, convert: Convert, conversion_page: Page
) -> None:
    """MF-33: once BIG is in a One to Many, its Conversion is read-only (createitem.component.ts:1763);
    KB `careportal_enriched_v5.csv#d890578b`: the transactions must be deleted first."""
    convert(one_to_many(conversion_items))
    open_item_for_change(conversion_page, conversion_items.big.product)
    expect_conversion_locked(conversion_page)
