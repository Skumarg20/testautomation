"""J06 GSTR-1 on screen and in the Excel export (an HTML table named .xls).

Read-only. The export is compared with the grid for the same period, never with hard-coded figures,
so other tests adding bills to the period cannot break it.
"""

import re

import pytest

from pages.reports.gst_export import ExportedReport, read_export
from pages.reports.gst_report_page import GstReportPage, ReportPeriod

pytestmark = [pytest.mark.p0, pytest.mark.journey("gst-reports")]

EXPORT_HEADER = (
    "Particulars",
    "No. of vouchers",
    "Taxable Value",
    "Integrated Tax",
    "Central Tax",
    "State Tax",
    "Cess",
    "Tax Amount",
    "Invoice Amount",
)
SCREEN_COLUMNS = EXPORT_HEADER[1:6]
COMPARED_ROWS = ("Taxable Sales", "HSN/SAC Summary")
AUGUST_2026 = ReportPeriod("01-08-2026", "31-08-2026")
TAX_COLUMNS = ("Integrated Tax", "Central Tax", "State Tax", "Cess")
PDF_SIGNATURE = b"%PDF-"
IFF_RETURN_TYPES = ("Monthly", "Quarterly")
BOOKS_YEAR_MONTHS = ("Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar")
IFF_ACTIONS = ("Excel", "JSON", "Cancel")


@pytest.fixture
def exported(gstr1: GstReportPage) -> ExportedReport:
    download = gstr1.export_excel()
    assert download.suggested_filename.startswith("GSTR-1 01-09-2026"), download.suggested_filename
    return read_export(gstr1.downloaded_file(download))


def test_export_header_row_lists_the_gstr1_columns(exported: ExportedReport) -> None:
    assert exported.header == EXPORT_HEADER


@pytest.mark.parametrize("particulars", COMPARED_ROWS)
def test_export_row_equals_the_grid_row_for_the_same_period(
    gstr1: GstReportPage, exported: ExportedReport, particulars: str
) -> None:
    on_screen = gstr1.screen_figures(particulars)

    in_export = {column: exported.figure(particulars, column) for column in on_screen}
    not_on_screen = {
        column: exported.figure(particulars, column) for column in SCREEN_COLUMNS if column not in on_screen
    }

    assert in_export == on_screen
    assert set(not_on_screen.values()) <= {0}


@pytest.mark.parametrize("particulars", COMPARED_ROWS)
def test_export_tax_amount_is_the_sum_of_its_tax_columns(exported: ExportedReport, particulars: str) -> None:
    tax_columns = sum(exported.figure(particulars, column) for column in TAX_COLUMNS)

    assert exported.figure(particulars, "Tax Amount") == tax_columns


def test_export_hsn_invoice_amount_is_taxable_value_plus_tax(exported: ExportedReport) -> None:
    row = "HSN/SAC Summary"
    expected = exported.figure(row, "Taxable Value") + exported.figure(row, "Tax Amount")

    assert exported.figure(row, "Invoice Amount") == expected


def test_report_title_follows_the_chosen_period(gstr1: GstReportPage) -> None:
    gstr1.set_period(AUGUST_2026)

    assert re.search(r"01-08-2026\s*(?:-To-|to)\s*31-08-2026", gstr1.period(), re.IGNORECASE)


def test_gstr3b_offers_the_json_export(gstr1: GstReportPage) -> None:
    gstr1.open_report("GSTR-3B")

    gstr1.expect_export_buttons(("btn-JSON",))


def test_gstr1_offers_the_return_and_summary_exports(gstr1: GstReportPage) -> None:
    gstr1.expect_export_buttons(("btn-GST Summary", "btn-GSTR1 Returns", "btn-IFF", "btn-Detail Excel"))


def test_pdf_export_downloads_a_pdf_file(gstr1: GstReportPage) -> None:
    download = gstr1.export_pdf()

    content = gstr1.downloaded_file(download).read_bytes()

    assert download.suggested_filename.endswith(".pdf"), download.suggested_filename
    assert content.startswith(PDF_SIGNATURE)


def test_iff_dialog_offers_each_return_type_and_month(gstr1: GstReportPage) -> None:
    gstr1.open_iff_dialog()

    gstr1.expect_iff_choices(IFF_RETURN_TYPES, BOOKS_YEAR_MONTHS)


def test_iff_dialog_offers_excel_json_and_cancel(gstr1: GstReportPage) -> None:
    gstr1.open_iff_dialog()

    gstr1.expect_iff_actions(IFF_ACTIONS)


def test_period_without_sales_exports_the_header_and_zero_taxable_sales(gstr1: GstReportPage) -> None:
    """August 2026 had no sales when this was written (checked live on 2026-10-08)."""
    gstr1.set_period(AUGUST_2026)

    exported = read_export(gstr1.downloaded_file(gstr1.export_excel()))

    assert exported.header == EXPORT_HEADER
    assert exported.figure("Taxable Sales", "Taxable Value") == 0
