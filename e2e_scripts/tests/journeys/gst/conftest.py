"""Fixtures for GST report tests on the garments tenant: GSTR-1 for a fixed period, E-Invoice Summary."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.reports.e_invoice_summary_page import EInvoiceSummaryPage
from pages.reports.gst_report_page import GstReportPage, ReportPeriod

GARMENTS: Account = "garments"
SEPTEMBER_2026 = ReportPeriod("01-09-2026", "30-09-2026")


@pytest.fixture
def gstr1(page_as: Callable[[Account], Page]) -> GstReportPage:
    page = page_as(GARMENTS)
    dashboard = DashboardPage(page)
    dashboard.open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    dashboard.expect_menu_items(("Report",))
    report = GstReportPage(page)
    report.open_report("GSTR-1")
    report.set_period(SEPTEMBER_2026)
    return report


@pytest.fixture
def e_invoice_summary(page_as: Callable[[Account], Page]) -> EInvoiceSummaryPage:
    """The E-Invoice Summary screen, freshly opened and not yet submitted. It never submits to the IRP."""
    page = page_as(GARMENTS)
    dashboard = DashboardPage(page)
    dashboard.open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    dashboard.expect_menu_items(("Report",))
    summary = EInvoiceSummaryPage(page)
    summary.open()
    return summary
