"""Offline checks of the Week 1 page objects against small HTML stubs served by a routed fake site."""

from decimal import Decimal
from typing import Any

import pytest
from playwright.sync_api import BrowserContext, Page, Route, expect

from pages.company_switch_page import CompanySwitchPage
from pages.components import access_denied
from pages.components.access_denied import AccessDenied, AccessDeniedError
from pages.purchase.garments.purchase_bill_page import PurchaseBillPage
from pages.reports.gst_report_page import GstReportPage, UnknownReportError

pytestmark = pytest.mark.framework

SITE = "http://stub.test"
BOOKS_YEAR_DASHBOARD = "/dashboard?books=25-26"
HEADER_HTML = """
<a id="dropdownMenuLink"><div id="txtheadercompname"><b class="cname">Garments New 29-08 </b></div>
<small> Books From <div> 01-04-2026 to 31-03-2027 </div></small></a>
"""
ORGANISATIONS_HTML = """
<div role="row"><div col-id="compname">Organisation Name</div></div>
<div role="row" ondblclick="location.href='/dashboard'">
  <div col-id="compname">Garments New 29-08 <svg><title>Current Active</title></svg></div></div>
<div role="row" ondblclick="location.href='/dashboard?books=25-26'">
  <div col-id="compname">25-26 Fy</div></div>
"""
PURCHASE_HTML = """
<input formcontrolname="ledgerName" id="txtLedgerName38">
<input formcontrolname="entryNo" id="txtentryNo38">
<input formcontrolname="BillValueAmount" value="1,180.000">
<input type="search" aria-label="Search" oninput="document.getElementById('hits').hidden = false">
<div id="hits" hidden>
  <div role="row" onclick="document.getElementById('txtLedgerName38').value='Mayur Sharma'">
    <div col-id="LedgerName">Mayur Sharma</div></div>
</div>
<button onclick="document.getElementById('dialog').remove()">Start Manual Entry</button>
<div id="dialog">How would you like to create your purchase bill?</div>
<div><div>Tax Info</div><div>CGST 9.00% : 90.000</div><div>SGST 9.00% : 90.000</div></div>
<button id="btnSave38" onclick="document.title = 'saved'">Save</button>
"""
REPORT_HTML = """
<span>GSTR-1 01-09-2026 to 30-09-2026</span>
<a href="data:application/octet-stream;base64,eGxzeC1ieXRlcw==" download="gstr1.xlsx" title="Excel">Excel</a>
<span>01-09-2026</span><span>-To-</span><span>30-09-2026</span>
<div role="row"><div role="columnheader">Particulars</div><div role="columnheader">No. of vouchers</div>
<div role="columnheader"> Taxable Value </div></div>
<div role="row"><div role="gridcell">Taxable Sales</div><div role="gridcell">1</div>
<div role="gridcell">444.00</div></div>
"""
PAGES = {
    "/user-company": HEADER_HTML + ORGANISATIONS_HTML,
    "/dashboard": HEADER_HTML + "<h1>Dashboard</h1>",
    BOOKS_YEAR_DASHBOARD: HEADER_HTML + "<h1>Dashboard</h1>",
    "/purchase": PURCHASE_HTML,
    "/report/gst/gstr1": REPORT_HTML,
    "/admin/users": "<script>location.replace('/dashboard')</script>",
    "/admin/roles": "<h1>Access Denied</h1>",
    "/admin/open": "<h1>Users</h1>",
}


def _serve(route: Route) -> None:
    path = route.request.url.removeprefix(SITE)
    if path in PAGES:
        route.fulfill(body=PAGES[path], content_type="text/html")
    else:
        route.fulfill(status=404, body="not found")


@pytest.fixture
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    return {**browser_context_args, "base_url": SITE}


@pytest.fixture
def site(context: BrowserContext, page: Page) -> Page:
    context.route(f"{SITE}/**", _serve)
    return page


def test_company_switch_reads_the_active_company_and_books_year(site: Page) -> None:
    site.goto("/dashboard")
    switcher = CompanySwitchPage(site)

    assert switcher.current_company() == "Garments New 29-08"
    assert switcher.current_year() == "01-04-2026 to 31-03-2027"


def test_switching_company_opens_its_dashboard(site: Page) -> None:
    CompanySwitchPage(site).switch_company("Garments New 29-08")

    expect(site).to_have_url(f"{SITE}/dashboard")


def test_switching_year_picks_the_books_year_row(site: Page) -> None:
    CompanySwitchPage(site).switch_year("25-26 Fy")

    expect(site).to_have_url(f"{SITE}{BOOKS_YEAR_DASHBOARD}")


def test_purchase_bill_chooses_supplier_and_reads_totals(site: Page) -> None:
    site.goto("/purchase")
    bill = PurchaseBillPage(site)

    bill.choose_supplier("Mayur Sharma")
    bill.start_manual_entry()
    bill.set_invoice_number("INV-1")

    expect(site.locator('input[formcontrolname="entryNo"]')).to_have_value("INV-1")
    assert bill.bill_value() == Decimal("1180.000")
    assert bill.tax_amounts() == {"CGST": Decimal("90.000"), "SGST": Decimal("90.000")}


def test_purchase_bill_save_presses_the_save_button(site: Page) -> None:
    site.goto("/purchase")

    PurchaseBillPage(site).save()

    expect(site).to_have_title("saved")


def test_gst_report_reads_period_and_taxable_value(site: Page) -> None:
    report = GstReportPage(site)

    report.open_report("GSTR-1")

    assert "01-09-2026" in report.period()
    assert report.taxable_value_of("Taxable Sales") == Decimal("444.00")


def test_gst_report_export_returns_the_downloaded_file(site: Page) -> None:
    report = GstReportPage(site)
    report.open_report("GSTR-1")

    exported = report.downloaded_file(report.export_excel())

    assert exported.read_bytes() == b"xlsx-bytes"


def test_gst_report_rejects_a_report_it_has_no_path_for(site: Page) -> None:
    with pytest.raises(UnknownReportError):
        GstReportPage(site).open_report("GSTR-9")


@pytest.mark.parametrize("path", ["/admin/users", "/admin/roles"])
def test_access_denied_accepts_a_redirect_or_a_denial_message(site: Page, path: str) -> None:
    AccessDenied(site).expect_denied(path)


def test_access_denied_fails_when_the_page_opens_normally(
    site: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(access_denied, "DENIAL_WAIT_MS", 500)

    with pytest.raises(AccessDeniedError):
        AccessDenied(site).expect_denied("/admin/open")
