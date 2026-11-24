"""Purchase checklist row 48: after a purchase the item master takes the last batch's sale rates D to H too,
and the purchase rate when the question "Update Change Rate" is answered Store.

Rates D to H are typed in the Batch Details window when the Control Room shows them (otherwise the test skips:
the window has no field to type in). The Item List shows `rated` .. `rateh` after `ratea`; the purchase
rate is
read from the item form (`#txtprate`). Everything the test changed is put back through the item form.
"""

from dataclasses import replace
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.inventory.item_list_page import ItemListPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE
from pages.purchase.documents.seed_documents import seed_draft
from pages.purchase.round2_c4.all_rates_bill import RatesNotOfferedError, RatesReader, StoringRateBill
from pages.sale.chemist.rate_validation_page import RateValidationPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

LETTERS = "adefgh"
RAISE = Decimal(3)
PURCHASE_RAISE = Decimal(7)
MRP_RAISE = Decimal(100)


def _restore_purchase_rate(page: Page, product: str, rate: Decimal) -> None:
    DashboardPage(page).open()
    form = ItemListPage(page)
    form.edit(product)
    page.locator("#txtprate").fill(format(rate, "f"))
    page.locator("#btnSave").click()


def test_item_master_takes_rates_d_to_h_and_the_stored_purchase_rate(pharma_page: Page) -> None:
    masters = RatesReader(pharma_page)
    product = masters.product_name_of(STANDARD_ITEM_CODE)
    originals = {letter: masters.rate_of(STANDARD_ITEM_CODE, f"rate{letter}") for letter in LETTERS}
    purchase_before = masters.purchase_rate_of(STANDARD_ITEM_CODE)
    typed = {letter: amount + RAISE for letter, amount in originals.items()}
    draft = seed_draft(timestamp_label())
    line = replace(draft.lines[0], rate=purchase_before + PURCHASE_RAISE)
    draft = draft.with_lines((line,))
    bills = StoringRateBill(pharma_page, originals["a"] + MRP_RAISE, typed)
    try:
        number = bills.create(draft)
    except RatesNotOfferedError as missing:
        pytest.skip(f"row 48: {missing}")
    try:
        for letter in LETTERS:
            assert masters.rate_of(STANDARD_ITEM_CODE, f"rate{letter}") == typed[letter]
        assert masters.purchase_rate_of(STANDARD_ITEM_CODE) == purchase_before + PURCHASE_RAISE
    finally:
        bills.delete(number)
        for letter, original in originals.items():
            DashboardPage(pharma_page).open()
            RateValidationPage(pharma_page).change_item_rate(product, letter, original)
        _restore_purchase_rate(pharma_page, product, purchase_before)
