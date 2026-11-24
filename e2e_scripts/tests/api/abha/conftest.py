"""Fixtures for the J39 API-level scenarios (AB-36..AB-38): two companies' sessions of the chemist login.

The sessions are taken from calls the app makes (`pages/abha/app_api.py`), because the suite's `api` fixture
has no login. The page is still armed with the ABHA `SendGuard`, so a screen opened on the way cannot reach
the ABDM proxy.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.abha.abdm_endpoints import ABDM_OR_ABHA_WRITE
from pages.abha.app_api import AppSession, CompanySession, OwnCompany
from pages.abha.patient_master import PatientMaster
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.dashboard_page import DashboardPage

ABHA_ACCOUNT: Account = "chemist"
OWN_COMPANY = PHARMA_COMPANY
OTHER_COMPANY = GARMENTS_COMPANY
MAX_PATIENTS_PROBED = 20


@pytest.fixture
def session_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    page = page_as(ABHA_ACCOUNT)
    guard = SendGuard(page, ABDM_OR_ABHA_WRITE)
    guard.arm()
    yield page
    guard.expect_nothing_sent()


@pytest.fixture
def own_company(session_page: Page) -> OwnCompany:
    """The ABHA company's session, taken from its patient-list call, and its own patients."""
    DashboardPage(session_page).open()
    CompanySwitchPage(session_page).ensure_company(OWN_COMPANY)
    app = AppSession(session_page)
    api, patients = app.patient_list_session(PatientMaster(session_page).open)
    if not patients:
        pytest.skip(f"AB-36..38 precondition: {OWN_COMPANY} has no patient of its own")
    return OwnCompany(CompanySession(api, app.session_ids()), patients)


@pytest.fixture
def other_company(session_page: Page, own_company: OwnCompany) -> CompanySession:
    """A second company of the same login; its session signs calls with its own company headers."""
    CompanySwitchPage(session_page).ensure_company(OTHER_COMPANY)
    app = AppSession(session_page)
    api = app.any_call_session(DashboardPage(session_page).open, own_company.session.api.controller_url)
    ids = app.session_ids()
    if ids.company_linkid == own_company.session.ids.company_linkid:
        pytest.skip(f"AB-36/37 precondition: {OTHER_COMPANY} must be a different company from {OWN_COMPANY}")
    return CompanySession(api, ids)


@pytest.fixture
def patient_with_abha_rows(own_company: OwnCompany) -> int:
    """AB-36: an own patient that has ABHA rows in its own company (read only, never seeded: decision N3)."""
    for patient in own_company.patient_linkids[:MAX_PATIENTS_PROBED]:
        if own_company.session.api.abha_rows_of(patient):
            return patient
    pytest.skip(
        f"AB-36 precondition: none of the first {MAX_PATIENTS_PROBED} patients of {OWN_COMPANY} has "
        "PatientAbhaDetails rows; the suite does not seed them (decision N3)"
    )
