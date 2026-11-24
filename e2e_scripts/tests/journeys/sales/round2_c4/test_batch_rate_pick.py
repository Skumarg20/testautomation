"""Sale bill row 11: the rate offered on a line is the chosen batch's rate, not the item master's.

Two batches of 44646015 are bought with different sale rates A (master + 20 and master + 40) through the Batch
Details window; the master follows the last one (+40). On a sale bill, picking the first batch shows
master + 20 in
the rate cell, the second master + 40: the rate follows the batch (default billing rate A; the batch
window passes
the batch's rates on, processinbatch.component.ts:1058-1066). The rates B to H are read from the batch
the same way
but only A is typed here. The tenant's master rate A and both purchases are put back afterwards.
The old option 'Pick Rates from Master/Batch' is commented out in the settings screen and has no reader.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.purchase.checklist.item_master_rates import ItemMasterRates
from pages.purchase.checklist.rated_bill import RatedPurchaseBill
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE
from pages.purchase.documents.seed_documents import seed_draft
from pages.sale.chemist.rate_validation_page import RateValidationPage
from pages.sale.documents.document_requests import parse_decimal
from pages.sale.documents.item_grid import PRICE
from pages.sale.manual.pharma_bill import ITEM, PharmaBill

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

FIRST_RAISE = Decimal(20)
SECOND_RAISE = Decimal(40)
MRP_RAISE = Decimal(100)


def test_rate_cell_shows_the_rate_of_the_chosen_batch(sales_page: Page, bill: PharmaBill) -> None:
    masters = ItemMasterRates(sales_page)
    product = masters.product_name_of(STANDARD_ITEM_CODE)
    original = masters.sale_rate_a_of(STANDARD_ITEM_CODE)
    first_rate, second_rate = original + FIRST_RAISE, original + SECOND_RAISE
    numbers: list[str] = []
    batches: list[str] = []
    try:
        for rate in (first_rate, second_rate):
            batch = timestamp_label()
            purchase = RatedPurchaseBill(sales_page, original + MRP_RAISE, rate)
            numbers.append(purchase.create(seed_draft(batch)))
            batches.append(batch)
        shown = []
        for batch in batches:
            bill.start()
            bill.document.grid.select_product(0, ITEM)
            bill.document.grid.choose_batch(0, batch)
            shown.append(parse_decimal(bill.document.grid.cell(0, PRICE).inner_text()))
            bill.leave_without_saving()
        assert shown == [first_rate, second_rate]
    finally:
        if bill.is_open():
            bill.leave_without_saving()
        for number in reversed(numbers):
            DashboardPage(sales_page).open()
            RatedPurchaseBill(sales_page, MRP_RAISE, original).delete(number)
        DashboardPage(sales_page).open()
        RateValidationPage(sales_page).change_item_rate(product, "a", original)
