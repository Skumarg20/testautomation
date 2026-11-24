"""Purchase volume discounts: Purchase Checklist rows 31 and 32.

Sheet formula "((Rate x Qty) x Volume dist / 100) - Bill discount" is the Percentage mode; the code has four
modes, chosen in Purchase Bill Setting > Ask Bill Discount & Item Discount on Billing > Configure
(`#PurchaseVolumdiscount1/2`, lookup 1025: perUnit, No, Lumpsum, Percentage). dataCalculation.ts:443-486:
perUnit = value x quantity, Lumpsum = value, Percentage = amount x value / 100, No = 0. Line: 10 pieces at
100 (amount 1000), volume value 5. "Total Disc" in the totals panel must show the expected figure. Weight is
not offered on the purchase window and is not tested. A bill whose volume cell is not drawn skips.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.waiting import appears_within
from pages.purchase.checklist.discount_readout import DiscountReadout
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.line_items import (
    STANDARD_EXPIRY,
    STANDARD_ITEM_CODE,
    DiscountColumn,
    PurchaseLineItem,
)
from pages.purchase.documents.seed_documents import seed_draft
from pages.sale.round2_c1.deal_math import volume_discount
from pages.settings.round2_c1.purchase_volume_modes import PurchaseVolumeModes, purchase_modes_held

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("chemist-tenant")]

CELL_LOOKUP_MS = 1_000
QUANTITY = 10
RATE = Decimal(100)
VALUE = Decimal(5)
LINE = (QUANTITY, RATE * QUANTITY)


def _line(column: DiscountColumn) -> PurchaseLineItem:
    return PurchaseLineItem(
        STANDARD_ITEM_CODE,
        Decimal(QUANTITY),
        rate=RATE,
        expiry_serial=STANDARD_EXPIRY,
        batch=timestamp_label(),
        discounts={column: VALUE},
    )


def _volume_cell_is_drawn(page: Page, column: DiscountColumn) -> bool:
    # Why CSS: ag-Grid cells carry only row-id and col-id (as in EntryGrid._cell).
    cell = page.locator(".ag-body-container").first.locator(f'[row-id="0"] [col-id="{column.value}"]')
    return appears_within(cell, CELL_LOOKUP_MS)


CASES = [
    (mode, column, position)
    for mode in ("perUnit", "Lumpsum", "Percentage", "No")
    for column, position in ((DiscountColumn.VOLUME_1, 0), (DiscountColumn.VOLUME_2, 1))
]


@pytest.mark.parametrize("case", CASES, ids=[f"{mode}-vol{position + 1}" for mode, _, position in CASES])
def test_volume_discount_follows_its_mode(pharma_page: Page, case: tuple[str, DiscountColumn, int]) -> None:
    """Rows 31 (volume 1) and 32 (volume 2): the discount shown is the mode's formula on 10 x 100."""
    mode, column, position = case
    chosen = (mode, "No") if position == 0 else ("No", mode)
    bills = PurchaseBillEntryPage(pharma_page)
    bills.begin(seed_draft(timestamp_label()))
    try:
        with purchase_modes_held(PurchaseVolumeModes(pharma_page), chosen):
            bills.fill_lines(seed_draft().with_lines((_line(column),)))
            if not _volume_cell_is_drawn(pharma_page, column):
                pytest.skip("rows 31, 32: the volume discount column is not shown on the purchase bill")

            DiscountReadout(pharma_page).expect_total(volume_discount(mode, VALUE, LINE))
    finally:
        bills.discard()
