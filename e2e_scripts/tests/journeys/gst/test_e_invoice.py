"""J20 e-invoice: the E-Invoice Summary list (Report > Statutory Report > E-Invoice) on the garments tenant.

Safety: no test generates, fetches or cancels an IRN. Those buttons submit to the government IRP through a GSP
and nothing proves the QA tenant uses a sandbox (spec `specs/e-invoice.md`, Q-EI-1). The tests only filter,
read and tick rows. They rely on the tenant's pending B2B bill 0000013 of 03-09-2026 (spec Preconditions).
"""

import pytest

from pages.reports.e_invoice_summary_page import EInvoiceBill, EInvoiceStatus, EInvoiceSummaryPage

pytestmark = [pytest.mark.p1, pytest.mark.journey("e-invoice")]

PENDING_B2B_BILL = EInvoiceBill(
    customer="Arun Sharma",
    gstin="33AAACT0763E1ZS",
    tax_type="Central",
    invoice_date="03-09-2026",
    invoice_no="0000013",
    bill_amount="568.00",
    taxable_value="444.00",
    tax_amount="124.32",
)
GRID_COLUMNS = (
    "Name of the Customer",
    "GSTIN",
    "Tax Type",
    "Invoice Date",
    "Invoice No",
    "Bill Amount",
    "Taxable Value",
    "Tax Amount",
)
FINANCIAL_YEAR_START = "01-04-2026"
FINANCIAL_YEAR_END = "31-03-2027"
IRN_ACTIONS = ("Generate", "Get IRN")


def test_ei01_summary_offers_status_filter_document_types_and_bill_columns(
    e_invoice_summary: EInvoiceSummaryPage,
) -> None:
    e_invoice_summary.expect_status_choices()
    e_invoice_summary.expect_document_types_unticked()
    e_invoice_summary.expect_columns(GRID_COLUMNS)


def test_ei06_this_year_period_spans_the_financial_year(e_invoice_summary: EInvoiceSummaryPage) -> None:
    e_invoice_summary.choose_period("This Year")

    e_invoice_summary.expect_period_dates(FINANCIAL_YEAR_START, FINANCIAL_YEAR_END)


def test_ei02_bill_to_registered_party_is_listed_with_gstin_and_amounts(
    e_invoice_summary: EInvoiceSummaryPage,
) -> None:
    e_invoice_summary.show_b2b_and_cdnr_bills("This Year", "All")

    e_invoice_summary.expect_bill_listed(PENDING_B2B_BILL)


def test_ei03_pending_filter_lists_bill_without_irn_and_counts_it(
    e_invoice_summary: EInvoiceSummaryPage,
) -> None:
    e_invoice_summary.show_b2b_and_cdnr_bills("This Year", "Pending")

    e_invoice_summary.expect_bill_listed(PENDING_B2B_BILL)
    assert e_invoice_summary.pending_count() >= 1


@pytest.mark.parametrize("status", ["Uploaded", "Cancelled"])
def test_ei04_bill_without_irn_is_not_listed_as_uploaded_or_cancelled(
    e_invoice_summary: EInvoiceSummaryPage, status: EInvoiceStatus
) -> None:
    e_invoice_summary.show_b2b_and_cdnr_bills("This Year", "All")
    e_invoice_summary.expect_bill_listed(PENDING_B2B_BILL)

    e_invoice_summary.choose_status(status)
    e_invoice_summary.submit()

    e_invoice_summary.expect_bill_not_listed(PENDING_B2B_BILL.invoice_no)


def test_ei16_irn_actions_appear_only_once_a_pending_bill_is_ticked(
    e_invoice_summary: EInvoiceSummaryPage,
) -> None:
    e_invoice_summary.show_b2b_and_cdnr_bills("This Year", "Pending")
    e_invoice_summary.expect_bill_listed(PENDING_B2B_BILL)
    e_invoice_summary.expect_actions_hidden(IRN_ACTIONS)

    e_invoice_summary.select_bill(PENDING_B2B_BILL.invoice_no)

    e_invoice_summary.expect_actions_offered(IRN_ACTIONS)
