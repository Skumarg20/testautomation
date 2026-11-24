"""Fixtures for the manual sale-bill cases (workbook "Sale Bill (Ajay)").

Pharma cases sell item 44646015 (batch 1231231123) to Cash Account in the pharma company; garments cases use
the parent conftest's `sale_page`. Teardown order, first to last: held settings are put back (that needs a
bill screen), the bill is left, then saved bills are deleted (that needs the list, so no bill may be open).
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.exempt_item import ExemptItem
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.masters.master_records import MasterRecords
from pages.sale.documents.flows import open_sales_page
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.sale.manual.garments_lines import ManualGarmentsSale
from pages.sale.manual.option_settings import HeldOptions, SaleBillSettings
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.manual.saved_bills import SavedBills
from test_data.masters import MasterDataFactory


def _already_open() -> None:
    """The garments bill is open for the whole test; nothing to open or close around a setting."""


@pytest.fixture
def pharma_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.fixture
def saved_bills(pharma_page: Page) -> Iterator[SavedBills]:
    """Bills the test saved through `saved_bills.save(bill)`; every one is deleted afterwards."""
    saved = SavedBills(pharma_page)
    yield saved
    saved.delete_all()


@pytest.fixture
def bill(pharma_page: Page, saved_bills: SavedBills) -> Iterator[PharmaBill]:
    new_bill = PharmaBill(pharma_page)
    yield new_bill
    if new_bill.is_open():
        new_bill.leave_without_saving()


@pytest.fixture
def options(pharma_page: Page, bill: PharmaBill) -> Iterator[HeldOptions]:
    """Hold sale bill settings for this test; the tenant's originals are put back before the bill is left.

    A setting needs an open bill: `hold` opens an empty one and closes it, so the test starts its own."""
    held = HeldOptions(SaleBillSettings(pharma_page), bill.document.open_new, bill.leave_without_saving)
    yield held
    held.close()


@pytest.fixture
def garments_options(sale_page: GarmentsSalePage) -> Iterator[HeldOptions]:
    """Control Room options held while a garments bill is open; put back before the bill is closed."""
    held = HeldOptions(SaleBillSettings(sale_page.page), _already_open, _already_open)
    yield held
    held.close()


@pytest.fixture
def manual_sale(sale_page: GarmentsSalePage) -> ManualGarmentsSale:
    return ManualGarmentsSale(sale_page.page)


GARMENTS_ACCOUNT: Account = "garments"


@pytest.fixture
def garments_dashboard(page_as: Callable[[Account], Page]) -> Page:
    """The garments login on the dashboard of the garments company."""
    page = page_as(GARMENTS_ACCOUNT)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    return page


@pytest.fixture
def owned_customer(garments_dashboard: Page, run_id: str) -> Iterator[str]:
    """A new customer ledger, deleted after the test (after its bills: fixtures tear down in reverse)."""
    records = MasterRecords(garments_dashboard, MasterDataFactory(run_id))
    try:
        name = records.saved_customer().name
        PartyAvailability(garments_dashboard).wait_until_selectable(name)
        yield name
    finally:
        records.delete_all()


@pytest.fixture
def exempt_item_name(garments_dashboard: Page) -> str:
    """The outstanding journey's 0% GST item, so a bill's total is its line amount."""
    return ExemptItem(garments_dashboard).ensure_exists()
