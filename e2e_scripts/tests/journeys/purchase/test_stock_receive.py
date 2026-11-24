"""Purchase stock receive: goods taken in against a supplier invoice raise stock; deleting gives it back."""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.item_stock import ItemStock
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.seed_documents import SEED_PARTY, seed_draft
from pages.purchase.documents.stock_receive_page import StockReceivePage

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

RECEIVED_VALUE = Decimal(
    9000
)  # 100 pieces at 100, less the 10% bill discount; the 50 free pieces cost nothing


def test_stock_receive_raises_stock_and_deleting_it_gives_the_stock_back(pharma_page: Page) -> None:
    receipts = StockReceivePage(pharma_page)
    stock = ItemStock(pharma_page)
    draft = seed_draft(timestamp_label())
    before = stock.snapshot(draft.lines)

    number = receipts.create(draft)

    stock.expect_received(draft.lines, before)
    receipts.menu.open_purchase(PurchaseScreen.STOCK_RECEIVE)
    receipts.documents.filter_this_week()
    receipts.documents.find(number)
    assert receipts.documents.party_of(number) == SEED_PARTY
    assert receipts.documents.amount_of(number) == RECEIVED_VALUE
    receipts.delete(number)
    stock.expect_back_to(before)
