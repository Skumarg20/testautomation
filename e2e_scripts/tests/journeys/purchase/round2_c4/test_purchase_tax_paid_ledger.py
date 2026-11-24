"""Purchase checklist row 46: a purchase from an unregistered supplier posts to the "Purchase Tax Paid"
ledger.

The tax-paid ledger is a fixed ledger (fixed id 36 for sale side, 37 for purchase,
InventoryProcess.cs:177-184;
the bill's tax row skips it, transactionin.businesslogic.ts:633). Support ticket MB-030737 shows it in
the ledger
register for a purchase from an unregistered party. The test makes an unregistered supplier, saves a pharma
purchase bill of the standard line to it, and looks for the bill number in the ledger report of
"Purchase Tax Paid"; the bill, then the supplier, are deleted. Whether the ledger report lists the voucher by
the bill's number is unverified live.
"""

from collections.abc import Iterator
from dataclasses import replace

import pytest
from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.masters.ledger_form import TaxRegistration
from pages.masters.master_records import MasterRecords
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.seed_documents import seed_draft
from pages.reports.ledger_report_page import LedgerReportPage
from test_data.masters import MasterDataFactory

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

TAX_PAID_LEDGER = "Purchase Tax Paid"


@pytest.fixture
def unregistered_supplier(pharma_page: Page, run_id: str) -> Iterator[str]:
    records = MasterRecords(pharma_page, MasterDataFactory(run_id))
    try:
        yield records.saved_gst_supplier(TaxRegistration.UNREGISTERED, "").name
    finally:
        DashboardPage(pharma_page).open()
        records.delete_all()


def test_unregistered_purchase_is_posted_to_the_purchase_tax_paid_ledger(
    pharma_page: Page, unregistered_supplier: str
) -> None:
    bills = PurchaseBillEntryPage(pharma_page)
    draft = replace(seed_draft(timestamp_label()), party=unregistered_supplier)
    number = bills.create(draft)
    try:
        report = LedgerReportPage(pharma_page)
        report.open_for(TAX_PAID_LEDGER)
        assert number in [line.voucher_number for line in report.lines()]
    finally:
        DashboardPage(pharma_page).open()
        bills.delete(number)
