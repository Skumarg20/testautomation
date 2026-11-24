"""J21 export and share from a report with data the test owns (specs/notifications-export.md, NE-19, NE-27).

The report is the ledger report of the test's own expense ledger (`ledger_book`, as in J12), so its rows
are exactly the test's vouchers and nobody else can change them.
"""

import re
from decimal import Decimal

import pytest

from pages.accounting.toasts import Toasts
from pages.banking.amounts import amount_in
from pages.banking.bank_book import BankBook
from pages.notifications_export.downloads import saved_file
from pages.notifications_export.report_share_export import ReportShareExport
from pages.reports.gst_export import ExportedReport, read_export
from pages.reports.ledger_report_page import LedgerReportPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

VoucherLine = tuple[str, str, Decimal, Decimal]
VOUCHER_COLUMNS = ("Vch/Bill No.", "Voucher Type", "₹ Debit", "₹ Credit")
FAKE_LINK_ID = "QA-share-link"
NO_WHATSAPP_NUMBER = re.compile(re.escape("Party Whatsapp Number not available."), re.IGNORECASE)


@pytest.fixture
def report_with_vouchers(ledger_book: BankBook) -> LedgerReportPage:
    """The expense ledger's report holding this test's payment and receipt."""
    ledger_book.record(ledger_book.ledgers.payment())
    ledger_book.record(ledger_book.ledgers.receipt())
    report = LedgerReportPage(ledger_book.page)
    report.open_for(ledger_book.ledgers.expense.name)
    return report


def test_excel_export_lists_every_voucher_shown_on_screen(
    ledger_book: BankBook, report_with_vouchers: LedgerReportPage
) -> None:
    """NE-19: the export holds the whole report, not only the rows in view (MBC-13152), with the same
    numbers, types and amounts, in the same order."""
    on_screen = [
        (line.voucher_number, line.voucher_type, line.debit, line.credit)
        for line in report_with_vouchers.lines()
    ]

    download = ReportShareExport(ledger_book.page).export_excel_current_view()

    assert _voucher_lines(read_export(saved_file(download))) == on_screen


def test_whatsapp_pdf_share_asks_for_the_number_and_sends_nothing_on_close(
    ledger_book: BankBook, report_with_vouchers: LedgerReportPage
) -> None:
    """NE-27: with the upload stubbed, What's App > PDF asks for a WhatsApp number; closing the dialog
    warns "Party Whatsapp Number not available." and nothing is sent. Live on 2026-10-12 the app said
    "Module Is Under Development" instead (D5), so this is expected to fail. (The report needs a voucher:
    the report of a ledger without one never shows its Total row.)"""
    share = ReportShareExport(ledger_book.page)
    share.stub_share_upload(FAKE_LINK_ID)

    share.share_pdf_on_whatsapp()
    share.expect_whatsapp_number_asked()
    share.close_whatsapp_dialog()

    Toasts(ledger_book.page).expect_any_saying(NO_WHATSAPP_NUMBER)


def _voucher_lines(exported: ExportedReport) -> list[VoucherLine]:
    """Rows that carry a voucher number (opening and total rows have none)."""
    indexes = [exported.header.index(column) for column in VOUCHER_COLUMNS]
    number, kind, debit, credit = indexes
    return [
        (row[number], row[kind], amount_in(row[debit]), amount_in(row[credit]))
        for row in exported.rows
        if len(row) > credit and row[number]
    ]
