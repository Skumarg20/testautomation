"""Purchase quotations: a price offer that moves no stock and can be pulled into an order."""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.purchase.documents.item_stock import ItemStock
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.order_page import PurchaseOrderPage
from pages.purchase.documents.quotation_page import PurchaseQuotationPage
from pages.purchase.documents.seed_documents import SEED_PARTY, seed_draft

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

# 100 pieces at 100 each, less the 10% bill discount of the standard draft; the 50 free pieces cost nothing.
QUOTED_VALUE = Decimal(9000)
CONVERTED_SKIP = (
    "J05 quotation -> order (no PU id): careportal:308770 describes pulling a quotation into a bill, not "
    "the list status it leaves; the mobile tech doc lists quotations as 'pending and billed' (onedrive:"
    "Technical Doc MB Mobile App_v1.0.docx#5.5); pending lists keep rows with remainingQty > 0 "
    "(datatype-reference.md, SaleChallanBill.cs:1223). Jira MBC-16523 reports 'Converted' shown wrongly on "
    "an order. Live, the row did not read 'Converted'. Question: what Status should a quotation fully "
    "pulled into an order show ('Converted', 'Billed', or still pending)?"
)


def test_quotation_is_listed_and_moves_no_stock(pharma_page: Page) -> None:
    quotations = PurchaseQuotationPage(pharma_page)
    stock = ItemStock(pharma_page)
    draft = seed_draft()
    before = stock.snapshot(draft.lines)

    number = quotations.create(draft)

    quotations.menu.open_purchase(PurchaseScreen.QUOTATION)
    quotations.documents.filter_this_week()
    quotations.documents.find(number)
    quotations.documents.expect_row_visible(number)
    assert quotations.documents.party_of(number) == SEED_PARTY
    assert quotations.documents.amount_of(number) == QUOTED_VALUE
    stock.expect_back_to(before)
    quotations.delete(number)


@pytest.mark.skip(reason=CONVERTED_SKIP)
def test_quotation_is_pulled_into_an_order_with_its_line(pharma_page: Page) -> None:
    quotations = PurchaseQuotationPage(pharma_page)
    orders = PurchaseOrderPage(pharma_page)
    quotation_number = quotations.create(seed_draft())

    order_number = orders.create(seed_draft().from_quotation(quotation_number))

    quotations.menu.open_purchase(PurchaseScreen.QUOTATION)
    quotations.documents.filter_this_week()
    quotations.documents.find(quotation_number)
    quotations.documents.expect_row_status(quotation_number, "Converted")
    orders.delete(order_number)
