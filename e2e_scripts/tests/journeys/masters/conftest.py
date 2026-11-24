"""Fixtures for the master CRUD tests: a garments session, the master screens and test-owned records."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from pages.masters.account_group_form import AccountGroupForm
from pages.masters.ledger_form import LedgerForm
from pages.masters.master_list import AccountGroupList, LedgerList
from pages.masters.master_records import MasterRecords
from test_data.masters import MasterDataFactory

# The account the accounting voucher tests use (tests/journeys/accounting/conftest.py).
MASTERS_ACCOUNT: Account = "garments"


@pytest.fixture
def masters_page(company_page: Callable[[Account, str], Page]) -> Page:
    page = company_page(MASTERS_ACCOUNT, GARMENTS_COMPANY)
    DashboardPage(page).expect_loaded()
    return page


@pytest.fixture
def records(masters_page: Page, run_id: str) -> Iterator[MasterRecords]:
    """Groups and ledgers owned by this test; whatever is still listed afterwards is deleted."""
    owned = MasterRecords(masters_page, MasterDataFactory(run_id))
    yield owned
    DashboardPage(masters_page).open()  # a fresh start: a failed test can leave a form or dialog open
    owned.delete_all()


@pytest.fixture
def ledger_list(masters_page: Page) -> LedgerList:
    return LedgerList(masters_page)


@pytest.fixture
def ledger_form(masters_page: Page) -> LedgerForm:
    return LedgerForm(masters_page)


@pytest.fixture
def group_list(masters_page: Page) -> AccountGroupList:
    return AccountGroupList(masters_page)


@pytest.fixture
def group_form(masters_page: Page) -> AccountGroupForm:
    return AccountGroupForm(masters_page)
