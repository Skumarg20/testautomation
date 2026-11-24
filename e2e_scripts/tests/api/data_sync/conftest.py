"""Fixtures for the DataSync service API tests of J35 (DS-19, DS-31, DS-44..DS-46).

The service is the DataSync host the web app's Data Sync screen calls (`pages/data_sync/sync_api.py`), not the
main API, so these tests build their own `ApiClient` for it instead of the root `api` fixture. The throwaway
company's ids are read from a browser session on that company, the way the app itself sends them.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.dashboard_page import DashboardPage
from pages.data_sync.sync_api import SyncRequestApi, data_sync_client
from pages.data_sync.sync_status_stub import CompanyKeys
from pages.data_sync.throwaway_company import ThrowawayCompany
from test_data.data_sync import THROWAWAY_COMPANY

DATA_SYNC_ACCOUNT: Account = "chemist"


@pytest.fixture
def sync_api(run_id: str) -> Iterator[SyncRequestApi]:
    client = data_sync_client(run_id)
    yield SyncRequestApi(client)
    client.close()


@pytest.fixture
def throwaway_keys(page_as: Callable[[Account], Page]) -> CompanyKeys:
    """The throwaway company's ids; skips when the chemist login has no such company."""
    page = page_as(DATA_SYNC_ACCOUNT)
    DashboardPage(page).open()
    company = ThrowawayCompany(page)
    if not company.is_listed(THROWAWAY_COMPANY):
        pytest.skip(f"DS-19/DS-45: needs the throwaway company {THROWAWAY_COMPANY!r} on the chemist login")
    company.select(THROWAWAY_COMPANY)
    return CompanyKeys.of_selected_company(page)
