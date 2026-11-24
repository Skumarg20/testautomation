"""Fixtures for the outstanding/advance cases: a new customer per test and the desks that act for it.

Decisions (test owner, 2026-10-09): each test owns a new customer ledger, so the report shows only that
test's documents; bills use one 0% GST test item so bill amounts equal the workbook's rupee values.
"""

import pytest
from playwright.sync_api import Page

from pages.accounting.outstanding.credit_desks import ReceiptDesk, SaleReturnDesk
from pages.accounting.outstanding.exempt_item import ExemptItem
from pages.accounting.outstanding.outstanding_report import OutstandingReport
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.accounting.outstanding.scenario import CaseDesks, CreditDocuments, OutstandingScenario
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.masters.master_records import MasterRecords
from test_data.masters import MasterDataFactory
from test_data.outstanding_steps import CreditKind


@pytest.fixture
def garments_company(accounting_page: Page) -> Page:
    """The shared QA login opens in whichever company it used last; on 2026-10-09 another run left it in
    the pharma company and a whole run created its data there. Every case works in the garments company."""
    CompanySwitchPage(accounting_page).ensure_company(GARMENTS_COMPANY)
    return accounting_page


@pytest.fixture
def customer(garments_company: Page, run_id: str) -> str:
    name = MasterRecords(garments_company, MasterDataFactory(run_id)).saved_customer().name
    PartyAvailability(garments_company).wait_until_selectable(name)
    return name


@pytest.fixture
def exempt_item(garments_company: Page) -> str:
    return ExemptItem(garments_company).ensure_exists()


@pytest.fixture
def scenario(accounting_page: Page, customer: str, exempt_item: str) -> OutstandingScenario:
    credits: dict[CreditKind, CreditDocuments] = {
        CreditKind.RECEIPT: ReceiptDesk(accounting_page),
        CreditKind.SALE_RETURN: SaleReturnDesk(accounting_page, exempt_item),
    }
    desks = CaseDesks(SaleBillDesk(accounting_page, exempt_item), credits, OutstandingReport(accounting_page))
    return OutstandingScenario(customer, desks)
