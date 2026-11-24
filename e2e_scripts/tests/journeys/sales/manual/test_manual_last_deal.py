"""Manual cases 138, 139, 140, 201, 202: the earlier deals the bill shows for the selected item.

Rule, from `processout.transaction.component.ts:7092-7134`: with "Last deal in Sale" not "No", selecting a row
asks for the item's earlier deals, by batch (`GetLastdealbybatch`, with the party) or by item and party
(`GetLastDealDetails`), and shows them in a table headed Bill No., Bill Date, Qty, Batch Name, S.Rate ...
(itemLastDealsDetail.component.html); with no earlier deal the table stays hidden (`itemBillHistoryShow` is
false). The earlier deal is the test's own bill, saved first and deleted by the `saved_bills` fixture.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.sale.manual.garments_lines import ManualGarmentsSale
from pages.sale.manual.option_settings import LAST_DEAL, HeldOptions
from pages.sale.manual.pharma_bill import LAST_DEAL_RATE_HEADER, PharmaBill
from pages.sale.manual.saved_bills import SavedBills

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)
GARMENTS_ITEM = "Sample Item"


def shows_the_earlier_bill(bill: PharmaBill, saved_bills: SavedBills) -> None:
    bill.start()
    bill.add_line(0, ONE)
    earlier = saved_bills.save(bill)

    bill.start()
    bill.pick_item(0, ONE)

    bill.expect_last_deal_lists(earlier)


def test_batch_wise_last_deal_lists_the_earlier_bill(
    options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills
) -> None:
    """Rows 201 and 140: the earlier deals of the batch."""
    options.hold(LAST_DEAL, "Batch Wise")

    shows_the_earlier_bill(bill, saved_bills)


def test_item_wise_last_deal_lists_the_earlier_bill(
    options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills
) -> None:
    """Rows 202 and 139: the earlier deals of the item for the party."""
    options.hold(LAST_DEAL, "Item Wise")

    shows_the_earlier_bill(bill, saved_bills)


def test_a_party_with_no_earlier_deal_sees_no_history(
    owned_customer: str, manual_sale: ManualGarmentsSale, garments_options: HeldOptions
) -> None:
    """Row 138: a new garments customer has bought nothing, so the table stays hidden and billing goes on."""
    garments_options.hold(LAST_DEAL, "Item Wise")
    manual_sale.choose_party(owned_customer)

    manual_sale.add_item(0, GARMENTS_ITEM, ONE)

    expect(manual_sale.page.get_by_role("table").filter(has_text=LAST_DEAL_RATE_HEADER)).to_have_count(0)
    manual_sale.expect_item_in_row(0, GARMENTS_ITEM)
