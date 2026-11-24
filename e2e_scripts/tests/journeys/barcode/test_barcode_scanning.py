"""J27 scanning an item's barcode into a garments sale bill. Nothing is saved: the bill is closed."""

import pytest

from pages.barcode.barcode_sale_bill import BarcodeSaleBill
from test_data.barcodes import SALE_PARTY
from test_data.models import ItemMasterSpec

pytestmark = [pytest.mark.p2, pytest.mark.journey("barcode-generation-scanning")]


def test_scanned_barcode_loads_its_item_on_the_bill_line(
    stocked_item: ItemMasterSpec, sale_bill: BarcodeSaleBill, barcode: str
) -> None:
    sale_bill.choose_party(SALE_PARTY)

    sale_bill.scan(barcode)

    sale_bill.expect_line(barcode, stocked_item.product)
