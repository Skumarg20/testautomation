"""Fixtures for the route / station / area tests: a garments session, the screens and test-owned records."""

from collections.abc import Callable, Iterator
from dataclasses import replace

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.masters.ledger_form import LedgerForm
from pages.masters.master_list import LedgerList
from pages.masters.master_records import MasterRecords
from pages.other_masters.master_forms import AreaForm, RouteForm, StationForm
from pages.other_masters.master_lists import AreaList, RouteList, StationList
from pages.other_masters.other_master_records import OtherMasterRecords
from test_data.masters import MasterDataFactory, PartyLedgerSpec
from test_data.other_masters import OtherMasterDataFactory

# The account and company the master CRUD tests use (tests/journeys/masters/conftest.py).
OTHER_MASTERS_ACCOUNT: Account = "garments"


@pytest.fixture
def masters_page(page_as: Callable[[Account], Page]) -> Page:
    page = page_as(OTHER_MASTERS_ACCOUNT)
    DashboardPage(page).open()
    # The login's company is shared state that other suites switch; the screens were observed on this one.
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    return page


@pytest.fixture
def records(masters_page: Page, run_id: str) -> Iterator[OtherMasterRecords]:
    """Routes, areas and stations owned by this test; whatever is still listed afterwards is deleted."""
    owned = OtherMasterRecords(masters_page, OtherMasterDataFactory(run_id))
    yield owned
    DashboardPage(masters_page).open()  # a fresh start: a failed test can leave a dialog open
    owned.delete_all()


@pytest.fixture
def ledgers(masters_page: Page, run_id: str, records: OtherMasterRecords) -> Iterator[MasterRecords]:
    """Ledgers owned by this test. Depends on `records` so the ledgers are deleted before the stations."""
    owned = MasterRecords(masters_page, MasterDataFactory(run_id))
    yield owned
    DashboardPage(masters_page).open()
    owned.delete_all()


@pytest.fixture
def route_form(masters_page: Page) -> RouteForm:
    return RouteForm(masters_page)


@pytest.fixture
def route_list(masters_page: Page) -> RouteList:
    return RouteList(masters_page)


@pytest.fixture
def area_form(masters_page: Page) -> AreaForm:
    return AreaForm(masters_page)


@pytest.fixture
def area_list(masters_page: Page) -> AreaList:
    return AreaList(masters_page)


@pytest.fixture
def station_form(masters_page: Page) -> StationForm:
    return StationForm(masters_page)


@pytest.fixture
def station_list(masters_page: Page) -> StationList:
    return StationList(masters_page)


@pytest.fixture
def ledger_list(masters_page: Page) -> LedgerList:
    return LedgerList(masters_page)


@pytest.fixture
def ledger_form(masters_page: Page) -> LedgerForm:
    return LedgerForm(masters_page)


@pytest.fixture
def customer_at_new_station(
    records: OtherMasterRecords, ledgers: MasterRecords, ledger_form: LedgerForm
) -> PartyLedgerSpec:
    """A saved customer ledger whose station is a station of this test."""
    customer = replace(ledgers.new_customer(), station=records.saved_station())
    ledger_form.open_new()
    ledger_form.enter_party(customer)
    ledger_form.save()
    ledger_form.expect_saved()
    return customer
