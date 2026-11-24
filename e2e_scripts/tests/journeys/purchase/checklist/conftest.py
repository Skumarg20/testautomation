"""Fixtures for the purchase checklist tests: an empty bill and a bill loaded from a challan."""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Page

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.challan_page import PurchaseChallanPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.seed_documents import seed_challan, seed_draft


@pytest.fixture
def empty_bill(pharma_page: Page) -> Iterator[PurchaseBillEntryPage]:
    """Purchase > Bill just after Create/F2: no party chosen yet; closed without saving."""
    bills = PurchaseBillEntryPage(pharma_page)
    bills.open_new()
    yield bills
    bills.discard()


@pytest.fixture
def bill_from_challan(pharma_page: Page) -> Iterator[PurchaseBillEntryPage]:
    """A bill that took over a saved challan's line (100 + 50 free at 100); the challan is deleted after."""
    challan_number = seed_challan(pharma_page)
    draft = seed_draft(timestamp_label()).from_challan(challan_number)
    bills = PurchaseBillEntryPage(pharma_page)
    bills.begin(draft)
    bills.enter_entry_date(draft.entry_date)
    bills.complete_header(draft)
    bills.grid.expect_line_carried(0, draft.lines[0])
    yield bills
    bills.discard()
    PurchaseChallanPage(pharma_page).delete(challan_number)
