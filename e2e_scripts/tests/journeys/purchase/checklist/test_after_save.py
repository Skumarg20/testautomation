"""Purchase checklist rows 26, 47 to 50 and 54: rate and stock after a purchase, and the page after Save.

Stock: a saved bill or challan adds quantity plus free quantity to the item, and the new batch holds the same
(the rule of tests/journeys/purchase/test_bill.py and test_challan.py, now read in all three places: Item
List, Batch List, Item Register; pages/stock/sale_impact/). Rates: the item master follows the last batch's
sale rate (sheet row 48); the test types its own rate A and puts the old one back through the item form.
After Save the bill page is new and blank with the cursor on the bill date (sheet rows 49 and 50).
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from pages.dashboard_page import DashboardPage
from pages.purchase.checklist.item_master_rates import ItemMasterRates
from pages.purchase.checklist.rate_cell import RateCell
from pages.purchase.checklist.rated_bill import RatedPurchaseBill
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.challan_page import PurchaseChallanPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.fields import labelled_input
from pages.purchase.documents.line_items import STANDARD_EXPIRY, STANDARD_ITEM_CODE
from pages.purchase.documents.seed_documents import seed_draft
from pages.sale.chemist.rate_validation_page import RateValidationPage
from pages.sale.documents.stock import StockLedger
from pages.stock.sale_impact.item_register import ItemRegister
from pages.stock.sale_impact.stock_views import StockReading, expect_reading, views_of

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

RECEIVED = Decimal(150)  # 100 pieces and 50 free
TYPED_RATE = Decimal(123)
RATE_A_RAISE = Decimal(50)
MRP_RAISE = Decimal(100)


@pytest.mark.parametrize("form_type", [PurchaseBillEntryPage, PurchaseChallanPage], ids=["bill", "challan"])
def test_saved_purchase_adds_to_item_list_batch_list_and_item_register(
    pharma_page: Page, form_type: type[PurchaseEntryForm]
) -> None:
    batch = timestamp_label()
    item_before = StockLedger(pharma_page).stock_of(STANDARD_ITEM_CODE)
    register_before = ItemRegister(pharma_page).closing_balance(STANDARD_ITEM_CODE)
    form = form_type(pharma_page)

    number = form.create(seed_draft(batch))

    expected = StockReading(item_before + RECEIVED, RECEIVED, register_before + RECEIVED)
    try:
        expect_reading(views_of(pharma_page, batch).read(), expected)
    finally:
        form.delete(number)


def test_page_after_save_is_blank_with_the_cursor_on_the_bill_date(pharma_page: Page) -> None:
    bills = PurchaseBillEntryPage(pharma_page)
    number = bills.create(seed_draft(timestamp_label()))
    try:
        bills.expect_vendor_empty()
        expect(labelled_input(pharma_page, "Entry Date")).to_be_focused()
    finally:
        bills.discard()
        bills.delete(number)


def test_rate_of_a_picked_item_is_the_purchase_rate_of_the_item_master(
    new_bill: PurchaseBillEntryPage,
) -> None:
    master_rate = ItemMasterRates(new_bill.page).purchase_rate_of(STANDARD_ITEM_CODE)
    new_bill.grid.select_product(0, STANDARD_ITEM_CODE)

    assert RateCell(new_bill.page).shown_rate(0) == master_rate


def test_typed_rate_replaces_the_rate_the_item_master_gave(new_bill: PurchaseBillEntryPage) -> None:
    """Row 27: the proposed rate is only a proposal; a rate typed after the quantity replaces it."""
    new_bill.grid.select_product(0, STANDARD_ITEM_CODE)
    new_bill.grid.type_batch(0, timestamp_label())
    new_bill.grid.enter_expiry(0, STANDARD_EXPIRY)
    new_bill.grid.enter_quantity(0, Decimal(1))

    new_bill.grid.enter_rate(0, TYPED_RATE)

    assert RateCell(new_bill.page).shown_rate(0) == TYPED_RATE


def test_item_master_takes_the_sale_rate_of_the_last_batch(pharma_page: Page) -> None:
    masters = ItemMasterRates(pharma_page)
    product = masters.product_name_of(STANDARD_ITEM_CODE)
    original = masters.sale_rate_a_of(STANDARD_ITEM_CODE)
    typed = original + RATE_A_RAISE
    bills = RatedPurchaseBill(pharma_page, original + MRP_RAISE, typed)
    number = bills.create(seed_draft(timestamp_label()))
    try:
        assert masters.sale_rate_a_of(STANDARD_ITEM_CODE) == typed
    finally:
        bills.delete(number)
        DashboardPage(pharma_page).open()
        RateValidationPage(pharma_page).change_item_rate(product, "a", original)
