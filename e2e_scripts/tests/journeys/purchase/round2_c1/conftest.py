"""Pharma purchase bill with Multi Unit on and an own item (QA-<run>-Item) holding a second unit of
10 pieces."""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Page

from pages.inventory.round2_c1.own_item import OwnItem
from pages.inventory.round2_c1.two_unit_own_item import two_unit_own_item
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import todays_serial
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.seed_documents import SEED_PARTY


@pytest.fixture
def two_unit_item(pharma_page: Page, run_id: str) -> Iterator[OwnItem]:
    with two_unit_own_item(pharma_page, run_id) as item:
        yield item


@pytest.fixture
def two_unit_bill(pharma_page: Page, two_unit_item: OwnItem) -> Iterator[PurchaseBillEntryPage]:
    bills = PurchaseBillEntryPage(pharma_page)
    bills.begin(PurchaseDraft(party=SEED_PARTY, entry_date=todays_serial()))
    bills.grid.select_product(0, two_unit_item.code)
    yield bills
    bills.discard()
