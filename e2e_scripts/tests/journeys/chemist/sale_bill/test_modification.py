"""Modifying a saved chemist sale bill: replace the item, change quantity, rate, discounts or batch."""

from collections.abc import Callable

import pytest

from pages.sale.chemist.sale_bill import SaleBill
from pages.settings.gst_configuration import GstType
from test_data.models import ItemEntry
from test_data.sale_items import A_TO_Z_NS, BIOZENTRA

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-modification"),
    pytest.mark.xdist_group("chemist-tenant"),
]

NEW_RATE = 1000
EXTRA_QUANTITY = 3
CHANGED_DISCOUNTS = ItemEntry(discount1=2, discount2=3, volume_discount1=4, volume_discount2=5)
BATCH_TO_SWITCH_TO = "E"


@pytest.fixture
def saved_bill(
    master_wise_barcodes: None, sale_bill: SaleBill, use_gst_type: Callable[[GstType], None]
) -> SaleBill:
    """A saved chemist bill with one item (scanned by its master barcode), reopened for modification."""
    sale_bill.start()
    use_gst_type("Exclusive")
    sale_bill.add_item(0, A_TO_Z_NS.by_barcode())
    sale_bill.save_and_reopen_for_modification()
    return sale_bill


def test_replacing_the_item_shows_the_new_item(saved_bill: SaleBill) -> None:
    saved_bill.replace_item(0, BIOZENTRA.by_description())

    assert BIOZENTRA.description in saved_bill.product_of(0)
    saved_bill.save_and_expect_saved()


def test_changing_the_quantity_updates_the_row(saved_bill: SaleBill) -> None:
    new_quantity = (A_TO_Z_NS.quantity or 0) + EXTRA_QUANTITY

    saved_bill.change_quantity(0, new_quantity)

    assert saved_bill.quantity_of(0) == new_quantity
    saved_bill.save_and_expect_saved()


def test_changing_the_rate_updates_the_row(saved_bill: SaleBill) -> None:
    saved_bill.change_sale_rate(0, NEW_RATE)

    assert saved_bill.sale_rate_of(0) == NEW_RATE
    saved_bill.save_and_expect_saved()


def test_changing_every_discount_updates_the_row(saved_bill: SaleBill) -> None:
    saved_bill.change_discounts(0, CHANGED_DISCOUNTS)

    assert saved_bill.discount1_of(0) == CHANGED_DISCOUNTS.discount1
    assert saved_bill.discount2_of(0) == CHANGED_DISCOUNTS.discount2
    assert saved_bill.volume_discount1_of(0) == CHANGED_DISCOUNTS.volume_discount1
    assert saved_bill.volume_discount2_of(0) == CHANGED_DISCOUNTS.volume_discount2
    saved_bill.save_and_expect_saved()


def test_changing_the_batch_keeps_the_bill_saveable(saved_bill: SaleBill) -> None:
    saved_bill.change_batch(0, BATCH_TO_SWITCH_TO)

    saved_bill.save_and_expect_saved()
