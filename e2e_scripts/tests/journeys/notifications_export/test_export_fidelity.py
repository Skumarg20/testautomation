"""J21 export and PDF fidelity (specs/notifications-export.md, NE-20..NE-24). Read-only except the test's own
customer, sale bill and ledgers, which teardown deletes. No file leaves the browser."""

import re

import pytest
from playwright.sync_api import Page

from pages.accounting.toasts import Toasts
from pages.banking.bank_book import BankBook
from pages.company_switch_page import GARMENTS_COMPANY
from pages.components.app_texts import EXPORT_DATA_NOT_FOUND
from pages.notifications_export.closing_stock_page import ClosingStockPage
from pages.notifications_export.downloads import saved_file
from pages.notifications_export.party_outstanding_page import PartyOutstandingPage
from pages.notifications_export.pdf_text import UNMAPPED, PdfText
from pages.notifications_export.report_share_export import ReportShareExport
from pages.notifications_export.sms_notification_page import SmsNotificationPage
from pages.reports.accounting_reports import TrialBalancePage
from pages.reports.gst_export import ExportedReport, read_export
from pages.reports.ledger_report_page import LedgerReportPage
from test_data.notifications_export import HINDI_WORD, OwnedBill

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

# Ledgers a receivable report must never carry (MB-037757: Cash, CGST, SGST rows in the export).
FOREIGN_LEDGER = re.compile(r"^(Cash|CGST|SGST|IGST)\b", re.IGNORECASE)
PAGE_HEADER = (GARMENTS_COMPANY, "Trial Balance")


@pytest.fixture
def receivable_export(garments_page: Page, customer_bill: OwnedBill) -> ExportedReport:
    """The Excel export of the test customer's receivable outstanding (Configure > Current View > Print)."""
    PartyOutstandingPage(garments_page).open_for(customer_bill.party)
    return read_export(saved_file(ReportShareExport(garments_page).export_excel_current_view()))


def test_receivable_export_lists_the_customers_bill(
    receivable_export: ExportedReport, customer_bill: OwnedBill
) -> None:
    """NE-20 (oracle): the export holds the bill the report shows."""
    assert any(customer_bill.number in cell for row in receivable_export.rows for cell in row)


def test_receivable_export_holds_no_cash_or_tax_ledgers(receivable_export: ExportedReport) -> None:
    """NE-20: no Cash, CGST, SGST or IGST row, which are not receivables (MB-037757)."""
    foreign = [cell for row in receivable_export.rows for cell in row if FOREIGN_LEDGER.match(cell.strip())]

    assert foreign == []


def test_export_of_an_empty_report_warns_and_saves_no_file(journey_page: Page) -> None:
    """NE-21 (N2): the generic export refuses an empty report with "Exporting data not found !" and no file
    (importexport.component.ts:292-295). Closing Stock Valuation is served the server's answer minus its
    rows."""
    report = ClosingStockPage(journey_page)
    report.open_without_rows()

    downloads = report.export()

    Toasts(journey_page).expect_any_saying(EXPORT_DATA_NOT_FOUND)
    assert downloads == []


def test_double_click_on_excel_saves_one_file(journey_page: Page) -> None:
    """NE-22: two clicks within a second (the export is limited to 2 calls a second) give one file."""
    report = SmsNotificationPage(journey_page)
    report.open()

    assert report.files_from_double_click_on_excel() == 1


def test_pdf_shows_a_hindi_ledger_name_as_text(hindi_ledger_book: BankBook) -> None:
    """NE-23 (MBC-13147): a report PDF of a ledger named in Hindi carries the Devanagari characters, none of
    them unmapped (a font without the script's glyphs prints black dots). The look itself is visual."""
    hindi_ledger_book.record(hindi_ledger_book.ledgers.payment())
    LedgerReportPage(hindi_ledger_book.page).open_for(hindi_ledger_book.ledgers.expense.name)

    first_page = PdfText(ReportShareExport(hindi_ledger_book.page).export_pdf_current_view()).pages()[0]

    assert first_page.shows_every_character_of(HINDI_WORD)
    assert UNMAPPED not in first_page.text


def test_second_pdf_page_repeats_the_report_header(garments_page: Page) -> None:
    """NE-24 (MB-031813): page 2 of a multi-page report PDF carries the header (company and report title).
    The Trial Balance of the shared garments company, expanded, stands in for a long ledger register."""
    report = TrialBalancePage(garments_page)
    report.open()
    report.expand_all()

    pages = PdfText(ReportShareExport(garments_page).export_pdf_current_view()).pages()

    if len(pages) < 2:
        pytest.skip("NE-24: needs a report longer than one PDF page; the Trial Balance fits on one")
    assert [pages[1].shows(text) for text in PAGE_HEADER] == [True, True]
