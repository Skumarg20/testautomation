"""Purchase checklist row 58: the rate of a line picked by barcode is the item master's purchase rate.

An item with a barcode and purchase rate 80 is created by the test (Control Room "Barcode Required" = Master
wise, restored afterwards) and removed at the end; it has no stock, so the item delete is allowed. On a new
purchase bill the item is found by its barcode and the rate cell shows 80 before anything is typed (the rate
from the master, as row 26 for the standard item). Rate from the batch: see test_rates_after_save.py and
test_all_rates_and_purchase_rate.py; parameter items are not covered.
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.purchase.checklist.rate_cell import RateCell
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.round2_c4.barcoded_item import BarcodedItem, BarcodedSpec
from pages.settings.control_room import BarcodeRequired
from pages.settings.control_room_state import ControlRoomState
from test_data.factory import DataFactory

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("chemist-tenant")]

PURCHASE_RATE = Decimal(80)
MASTER_WISE: BarcodeRequired = "Master wise"


@pytest.fixture
def barcode_master_wise(pharma_page: Page) -> Iterator[None]:
    room = ControlRoomState(pharma_page)
    original = room.current_barcode_required()
    room.set_barcode_required(MASTER_WISE)
    try:
        yield
    finally:
        DashboardPage(pharma_page).open()
        room.set_barcode_required(original)


@pytest.fixture
def barcoded_item(pharma_page: Page, run_id: str, barcode_master_wise: None) -> Iterator[BarcodedItem]:
    data = DataFactory(run_id)
    barcode = f"8{int(run_id, 16) % 10**11:011d}"
    item = BarcodedItem(pharma_page, BarcodedSpec(data.item_master(), barcode, PURCHASE_RATE))
    item.create()
    try:
        yield item
    finally:
        item.delete()


def test_rate_of_an_item_picked_by_barcode_is_its_purchase_rate(
    pharma_page: Page, new_bill: PurchaseBillEntryPage, barcoded_item: BarcodedItem
) -> None:
    barcoded_item.pick_on_purchase_line(new_bill.grid, 0)

    assert RateCell(pharma_page).shown_rate(0) == PURCHASE_RATE
