"""Purchase checklist row 48: after a purchase the item master takes the last batch's sale rates B and C too.

Extends `test_item_master_takes_the_sale_rate_of_the_last_batch` (rate A). Rates are raised by 5 and 6
over the
Item List's, a bill is saved, the Item List must show them, then the bill is deleted and the old rates are put
back through the item form. The purchase rate is not changed here (the app asks whether to store it).
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE
from pages.purchase.documents.seed_documents import seed_draft
from pages.purchase.round2_c4.all_rates_bill import AllRatesPurchaseBill, RatesReader
from pages.sale.chemist.rate_validation_page import RateValidationPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

RAISE_B = Decimal(5)
RAISE_C = Decimal(6)
MRP_RAISE = Decimal(100)


def test_item_master_takes_sale_rates_b_and_c_of_the_last_batch(pharma_page: Page) -> None:
    masters = RatesReader(pharma_page)
    product = masters.product_name_of(STANDARD_ITEM_CODE)
    original_a = masters.sale_rate_a_of(STANDARD_ITEM_CODE)
    original_b = masters.rate_of(STANDARD_ITEM_CODE, "rateb")
    original_c = masters.rate_of(STANDARD_ITEM_CODE, "ratec")
    rates = {"a": original_a, "b": original_b + RAISE_B, "c": original_c + RAISE_C}
    bills = AllRatesPurchaseBill(pharma_page, original_a + MRP_RAISE, rates)
    number = bills.create(seed_draft(timestamp_label()))
    try:
        assert masters.rate_of(STANDARD_ITEM_CODE, "rateb") == rates["b"]
        assert masters.rate_of(STANDARD_ITEM_CODE, "ratec") == rates["c"]
    finally:
        bills.delete(number)
        for letter, original in (("a", original_a), ("b", original_b), ("c", original_c)):
            DashboardPage(pharma_page).open()
            RateValidationPage(pharma_page).change_item_rate(product, letter, original)
