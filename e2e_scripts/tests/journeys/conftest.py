"""Shared setup for the browser journey suites."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import CompanySwitchPage
from pages.dashboard_page import DashboardPage

# The zz_probe_* packages are planning probes: they save records in the shared tenant and assert nothing,
# so a normal run must not collect them. Pytest still runs one whose test file is named on the command line.
collect_ignore_glob = ["zz_probe_*"]


@pytest.fixture
def company_page(page_as: Callable[[Account], Page]) -> Callable[[Account, str], Page]:
    """Opens the dashboard of an account's session, pinned to one company.

    The login's company is shared state that other suites switch, so each suite pins the company its plan
    was observed on."""

    def open_on(account: Account, company: str) -> Page:
        page = page_as(account)
        DashboardPage(page).open()
        CompanySwitchPage(page).ensure_company(company)
        return page

    return open_on
