"""J27 barcode on the item master: a typed barcode is kept, and the duplicate rule.

The duplicate test switches a tenant-wide Control Room choice and restores it (xdist group)."""

import pytest

from pages.barcode.barcoded_item import BarcodedItem
from test_data.models import ItemMasterSpec

pytestmark = [pytest.mark.p2, pytest.mark.journey("barcode-generation-scanning")]


def test_barcode_typed_on_create_is_kept_on_the_item(
    barcoded_item: BarcodedItem, saved_item: ItemMasterSpec, barcode: str
) -> None:
    barcoded_item.expect_barcode_on_edit(saved_item.product, barcode)


@pytest.mark.xdist_group("chemist-tenant")
@pytest.mark.usefixtures("duplicates_forbidden", "saved_item")
def test_second_item_with_the_same_barcode_is_refused_when_duplicates_are_not_allowed(
    barcoded_item: BarcodedItem, twin: ItemMasterSpec, barcode: str
) -> None:
    barcoded_item.try_create(twin, barcode)

    barcoded_item.expect_not_saved(twin.product)
