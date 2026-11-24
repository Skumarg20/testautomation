"""Purchase checklist rows that stay skipped or are scripted as a negative, each with the reason.

Rows 16 to 21 and 23 (two-unit purchase), 31 and 32 (volume discount), 40 (mode of payment), 56 to 58.
"""

import pytest
from playwright.sync_api import expect

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

NET_PROFIT_TIMEOUT_MS = 2_500


def test_alt_f10_opens_no_profit_window_on_a_purchase_bill(new_bill: PurchaseBillEntryPage) -> None:
    """Checklist rows 56 and 57. The Net Profit window (`NetProfitWindow`) is opened by Alt+F10 on the sale
    screens only (processout.transaction.component.ts:15297-15298); the purchase screen's key handler
    (transactionin.component.ts:14440-14650) has no Alt+F10, and its pink loss row class is never set. So the
    purchase bill shows no profit window; whether the row was meant for sales is the open question."""
    new_bill.grid.select_product(0, STANDARD_ITEM_CODE)

    new_bill.page.keyboard.press("Alt+F10")

    profit = new_bill.page.get_by_text("Net Profit")
    expect(profit).to_have_count(0, timeout=NET_PROFIT_TIMEOUT_MS)


def test_rate_of_a_picked_item_comes_from_the_item_master_only() -> None:
    pytest.skip(
        "checklist row 58: rate from batch, parameter and barcode entry on purchase has no known "
        "QA item with a barcode or parameter group; rate from the master is test_after_save.py"
    )
