"""J21 SMS Notification report and its exports (specs/notifications-export.md, NE-14..NE-18, NE-25, NE-43).

Read-only. The log belongs to the signed-in user (it was empty for the QA chemist login on 2026-10-12),
so the export is compared with the grid of the same moment, never with fixed figures.
"""

import re

import pytest
from playwright.sync_api import Page

from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.components.app_texts import EXPORT_DATA_NOT_FOUND
from pages.notifications_export.downloads import saved_file
from pages.notifications_export.export_heading import read_heading
from pages.notifications_export.sms_notification_page import TITLE, SmsNotificationPage
from pages.reports.gst_export import read_export

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

GRID_COLUMNS = ("Show Use Date", "Mobile No", "Module Name", "Message", "No of SMS")
EXPORT_COLUMNS = ("Date", "SendTo", "NotificationType", "Content", "Unit")
EXCEL_FILE_NAME = f"{TITLE}.xls"
PDF_SIGNATURE = b"%PDF-"
DATE = re.compile(r"\d{2}-\d{2}-\d{4}")


@pytest.fixture
def report(journey_page: Page) -> SmsNotificationPage:
    screen = SmsNotificationPage(journey_page)
    screen.open()
    return screen


@pytest.fixture
def empty_report(journey_page: Page) -> SmsNotificationPage:
    screen = SmsNotificationPage(journey_page)
    screen.serve_empty_log()
    screen.open()
    return screen


@pytest.fixture
def books_year(journey_page: Page) -> list[str]:
    """Start and end date of the company's books year, as the header shows them."""
    return DATE.findall(CompanySwitchPage(journey_page).current_year())


def test_report_shows_the_sms_log_columns(report: SmsNotificationPage) -> None:
    """NE-14: heading "SMS Notification" and the grid columns (K4: the KB names other columns)."""
    report.expect_columns(GRID_COLUMNS)


def test_report_period_is_the_books_year(report: SmsNotificationPage, books_year: list[str]) -> None:
    """NE-14: the read-only period label shows the books year, "<from> -To-<to>"."""
    start, end = books_year

    report.expect_period(re.compile(rf"{start}\s*-To-\s*{end}"))


def test_back_returns_to_the_combined_report(report: SmsNotificationPage) -> None:
    """NE-14 / K5: Back goes to Reports > Combined Report (the Management Report group)."""
    report.go_back()


def test_excel_export_is_named_after_the_report_with_its_columns(report: SmsNotificationPage) -> None:
    """NE-15: `SMS Notification.xls` (an HTML table) with the export's own column names."""
    download = report.export_excel()

    exported = read_export(saved_file(download))

    assert download.suggested_filename == EXCEL_FILE_NAME
    assert exported.header == EXPORT_COLUMNS


def test_excel_export_has_one_row_per_grid_row(report: SmsNotificationPage) -> None:
    """NE-15: every message in the grid is a row in the export, no more and no fewer."""
    on_screen = report.grid_row_count()

    exported = read_export(saved_file(report.export_excel()))

    assert len(exported.rows) == on_screen


def test_excel_export_period_is_the_books_year(report: SmsNotificationPage, books_year: list[str]) -> None:
    """NE-17: the export heading should show the period on screen (books start To books end).
    The code passes the books start as To (K3), so this is expected to fail (D2)."""
    start, end = books_year

    heading = read_heading(saved_file(report.export_excel()))

    assert DATE.findall(heading.period) == [start, end]


def test_excel_export_names_the_current_company(report: SmsNotificationPage) -> None:
    """NE-43 (single company): the export heading names the company the user works in (pinned)."""
    heading = read_heading(saved_file(report.export_excel()))

    assert heading.company == GARMENTS_COMPANY


def test_pdf_export_opens_a_new_tab_with_a_pdf(report: SmsNotificationPage) -> None:
    """NE-16: PDF builds the file on the server (Common/GetReportData) and opens it in a new tab.
    Headless Chromium has no PDF viewer, so the tab stays about:blank; the bytes are checked instead."""
    pdf = report.export_pdf()

    assert pdf.startswith(PDF_SIGNATURE)


def test_print_icon_opens_the_pdf_view(report: SmsNotificationPage) -> None:
    """NE-25: the print icon opens the same PDF in a new tab; nothing goes to a printer."""
    printed = report.print_report()

    assert printed.startswith(PDF_SIGNATURE)


def test_excel_export_of_an_empty_report_warns_and_saves_no_file(empty_report: SmsNotificationPage) -> None:
    """NE-18 (N2 decided 2026-10-12): with no rows the app's shared export refuses with "Exporting data not
    found !" (sharedexportimport.ts:99-102). This screen exports a header-only file instead (D7)."""
    downloads = empty_report.click_excel()

    empty_report.expect_message(EXPORT_DATA_NOT_FOUND)
    assert downloads == []
