"""Fixtures for the purchase tests: the garments Alt+P window, and the pharma Purchase > Bill screen."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY
from pages.components.bill_totals import BillTotals
from pages.dashboard_page import DashboardPage
from pages.masters.ledger_form import TaxRegistration
from pages.masters.master_records import MasterRecords
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import todays_serial
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.seed_documents import SEED_PARTY
from pages.purchase.documents.support import open_dashboard
from pages.purchase.garments.purchase_bill_page import PurchaseBillPage
from test_data.factory import DataFactory
from test_data.masters import MasterDataFactory
from test_data.models import HOME_STATE_CODE

GARMENTS: Account = "garments"


@pytest.fixture
def purchase_page(company_page: Callable[[Account, str], Page]) -> Iterator[PurchaseBillPage]:
    page = company_page(GARMENTS, GARMENTS_COMPANY)
    DashboardPage(page).expect_menu_items(("Purchase",))
    bill = PurchaseBillPage(page)
    bill.open()
    yield bill
    BillTotals(page).leave_without_saving()


@pytest.fixture
def totals(purchase_page: PurchaseBillPage) -> BillTotals:
    return BillTotals(purchase_page.page)


@pytest.fixture
def pharma_page(page_as: Callable[[Account], Page]) -> Page:
    return open_dashboard(page_as)


@pytest.fixture
def new_bill(pharma_page: Page) -> Iterator[PurchaseBillEntryPage]:
    """Purchase > Bill with the supplier chosen and no line entered; closed without saving."""
    bills = PurchaseBillEntryPage(pharma_page)
    bills.begin(PurchaseDraft(party=SEED_PARTY, entry_date=todays_serial()))
    yield bills
    bills.discard()


def _gst_supplier(page: Page, run_id: str, registration: TaxRegistration) -> Iterator[str]:
    """A supplier of this test in the company's own state, with a GSTIN; deleted afterwards."""
    DashboardPage(page).expect_loaded()
    records = MasterRecords(page, MasterDataFactory(run_id))
    try:
        gstin = DataFactory(run_id).valid_gstin(HOME_STATE_CODE)
        yield records.saved_gst_supplier(registration, gstin).name
    finally:
        DashboardPage(page).open()
        records.delete_all()


@pytest.fixture
def intra_state_supplier(company_page: Callable[[Account, str], Page], run_id: str) -> Iterator[str]:
    yield from _gst_supplier(company_page(GARMENTS, GARMENTS_COMPANY), run_id, TaxRegistration.REGISTERED)


@pytest.fixture
def composition_supplier(company_page: Callable[[Account, str], Page], run_id: str) -> Iterator[str]:
    yield from _gst_supplier(company_page(GARMENTS, GARMENTS_COMPANY), run_id, TaxRegistration.COMPOSITION)
