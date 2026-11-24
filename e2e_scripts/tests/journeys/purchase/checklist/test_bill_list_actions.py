"""Purchase checklist rows 51 and 52: Print and Export from the purchase bill list.

Print opens the Print window of the selected bill (transactionin.list.component.ts:1218-1265); its Preview
button is shown and the window is closed again, so nothing reaches a printer. Export downloads a file
(:1292-1294). Button names are from the source and unverified live.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.purchase.checklist.list_actions import BillListActions
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.seed_documents import seed_draft

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]


@pytest.fixture
def listed_bill(pharma_page: Page) -> str:
    """A saved bill, found in the list with its row ready to select; deleted by the test that uses it."""
    bills = PurchaseBillEntryPage(pharma_page)
    number = bills.create(seed_draft(timestamp_label()))
    bills.menu.open_purchase(PurchaseScreen.BILL)
    bills.documents.filter_this_week()
    bills.documents.find(number)
    bills.documents.expect_row_visible(number)
    return number


def test_print_from_the_bill_list_opens_the_print_window(pharma_page: Page, listed_bill: str) -> None:
    actions = BillListActions(pharma_page)
    try:
        expect(actions.print_window_for(listed_bill)).to_be_visible()
        actions.close_print_window()
    finally:
        PurchaseBillEntryPage(pharma_page).delete(listed_bill)


def test_export_from_the_bill_list_downloads_a_file(pharma_page: Page, listed_bill: str) -> None:
    try:
        download = BillListActions(pharma_page).export_selected(listed_bill)
        assert re.search(r"\.\w+$", download.suggested_filename)
    finally:
        PurchaseBillEntryPage(pharma_page).delete(listed_bill)
