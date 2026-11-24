"""Offline checks of the batch B page objects (sale, purchase, GST report) against small HTML stubs."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import BrowserContext, Page, Route, expect

from pages.components.bill_totals import BillTotals
from pages.components.shortcut import ShortcutIgnoredError, press_until_visible
from pages.purchase.garments.purchase_bill_page import GarmentsPurchaseLine, PurchaseBillPage
from pages.reports.gst_export import ExportRowNotFoundError, read_export
from pages.reports.gst_report_page import GstReportPage, ReportPeriod
from pages.sale.garments.garments_sale_page import GarmentsSalePage

pytestmark = pytest.mark.framework

SITE = "http://stub-b.test"
TOTALS_HTML = """
<div class="ag-body-container">
  <div class="ag-row"><div col-id="ledgerLinkID">SGST Output</div><div col-id="amount"> 7.500</div></div>
  <div class="ag-row"><div col-id="ledgerLinkID"></div><div col-id="amount"></div></div>
</div>
<div><div class="bill-value-text">Invoice Value : ₹ 1,083.000</div></div>
<button id="btnEsc88" onclick="document.getElementById('ask').hidden=false">Close</button>
<div id="ask" hidden>Are you sure? <button id="btnYes" onclick="document.title='left'">Yes</button></div>
"""
SALE_HTML = """
<input id="txtLedgerName7" oninput="document.getElementById('party').hidden=false">
<input id="txtStore7">
<div id="party" role="dialog" hidden><h4>Select Party</h4><div role="row"><div role="gridcell" onclick="
  document.getElementById('grid').hidden=false">Ajay</div></div></div>
<div id="grid" hidden>
  <input id="txt-tmp_barcode-0"
    onkeydown="if(event.key==='Enter')document.getElementById('picker').hidden=false">
  <input id="txt-tmp_barcode-1" hidden>
  <div class="ag-body-container"><div class="ag-row"><div col-id="itemLinkID"></div>
    <div col-id="DisplayAmount" id="amount"></div></div></div>
</div>
<div id="picker" hidden><input id="searchItems" oninput="hit.hidden=false"
  onkeydown="if(event.key==='Enter'&&variants.hidden){event.stopPropagation();variants.hidden=false}">
  <div id="hit" hidden class="ag-row ag-row-selected"><div col-id="Product">Sample Item</div></div>
  <div id="variants" hidden class="ag-row ag-row-selected"><div col-id="balanceQty">981.000</div></div></div>
<div id="qtywin" hidden><input id="txt-qty-0"></div>
<script>
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !variants.hidden && qtywin.hidden) {
    qtywin.hidden = false; document.getElementById('txt-qty-0').focus(); }
  if (e.key === 'F10' && !qtywin.hidden) {
    document.getElementById('amount').textContent =
      (document.getElementById('txt-qty-0').value * 100).toFixed(3);
    document.getElementById('txt-tmp_barcode-1').hidden = false; } });
</script>
"""
GST_HTML = """
<div id="title">GSTR-1 01-09-2026 to 30-09-2026</div>
<div class="ag-row"><div col-id="Particulars">Taxable Sales</div><div col-id="Vouchers">1</div>
 <div col-id="TaxableValue">444.00</div><div col-id="IntegratedTax">124.32</div>
 <div col-id="CentralTax"></div><div col-id="StateTax">0.00</div></div>
<div id="filter" hidden><input id="fromDateFilter"><input id="toDateFilter">
 <button id="btn-Ok" onclick="document.getElementById('title').textContent='GSTR-1 '
 +fromDateFilter.value+' to '+toDateFilter.value">OK</button></div>
<script>document.addEventListener('keydown', e => { if (e.altKey && e.code === 'KeyD')
 document.getElementById('filter').hidden = false; });</script>
<button id="btn-JSON">JSON</button>
"""
EXPORT_HTML = """
<table><tr><td>GSTR-1 01-09-2026 to 30-09-2026</td></tr>
<tr><th>Particulars</th><th>No. of vouchers</th><th>Taxable Value</th><th>Tax Amount</th></tr>
<tr><td> Taxable Sales </td><td>1</td><td>1,444.00</td><td>124.32</td></tr>
<tr><td>Nil Rated</td><td></td><td></td><td></td></tr></table>
"""


def _serve(route: Route) -> None:
    path = route.request.url.removeprefix(SITE)
    pages = {"/totals": TOTALS_HTML, "/sale": SALE_HTML, "/gst": GST_HTML, "/blank": "<p>nothing</p>"}
    if path in pages:
        route.fulfill(body=pages[path], content_type="text/html; charset=utf-8")
    else:
        route.fulfill(status=404, body="not found")


@pytest.fixture
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    return {**browser_context_args, "base_url": SITE}


@pytest.fixture
def site(context: BrowserContext, page: Page) -> Page:
    context.route(f"{SITE}/**", _serve)
    return page


def test_bill_totals_reads_tax_rows_and_invoice_value(site: Page) -> None:
    site.goto("/totals")
    totals = BillTotals(site)

    assert totals.tax_amounts() == {"SGST Output": Decimal("7.500")}
    assert totals.invoice_value() == Decimal("1083.000")


def test_bill_totals_waits_for_expected_values(site: Page) -> None:
    site.goto("/totals")
    totals = BillTotals(site)

    totals.expect_invoice_value(Decimal("1083"))
    totals.expect_tax_amounts({"SGST Output": Decimal("7.5")})


def test_bill_totals_fails_when_the_value_is_not_shown(site: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pages.components.bill_totals.CALCULATION_TIMEOUT_MS", 300)
    site.goto("/totals")

    with pytest.raises(AssertionError):
        BillTotals(site).expect_invoice_value(Decimal("1083.001"))


def test_leaving_without_saving_confirms_the_discard_prompt(site: Page) -> None:
    site.goto("/totals")

    BillTotals(site).leave_without_saving()

    expect(site).to_have_title("left")


def test_leaving_an_untouched_bill_needs_no_confirmation(site: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pages.components.bill_totals.DISCARD_PROMPT_TIMEOUT_MS", 300)
    site.goto("/totals")
    site.evaluate("document.getElementById('btnEsc88').onclick = null")

    BillTotals(site).leave_without_saving()


def test_garments_sale_page_adds_an_item_and_reads_the_line_amount(site: Page) -> None:
    site.goto("/sale")
    sale = GarmentsSalePage(site)

    sale.choose_party("Ajay")
    sale.add_item(0, "Sample Item", Decimal(3))

    assert sale.line_amount(0) == Decimal("300.000")
    sale.expect_line_amount(0, Decimal(300))


def test_shortcut_helper_gives_up_when_the_screen_never_opens(
    site: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pages.components.shortcut.ATTEMPT_TIMEOUT_MS", 200)
    site.goto("/blank")

    with pytest.raises(ShortcutIgnoredError):
        press_until_visible(site, "Alt+N", site.locator("#never"))


def test_gst_report_reads_screen_figures_and_changes_period(site: Page) -> None:
    site.goto("/gst")
    report = GstReportPage(site)

    assert report.screen_figures("Taxable Sales") == {
        "No. of vouchers": Decimal(1),
        "Taxable Value": Decimal("444.00"),
        "Integrated Tax": Decimal("124.32"),
        "Central Tax": Decimal(0),
        "State Tax": Decimal("0.00"),
    }
    report.set_period(ReportPeriod("01-08-2026", "31-08-2026"))
    assert "01-08-2026 to 31-08-2026" in report.period()
    report.expect_export_buttons(("btn-JSON",))


def test_export_is_read_as_an_html_table(tmp_path: Path) -> None:
    exported_file = tmp_path / "GSTR-1.xls"
    exported_file.write_text(EXPORT_HTML, encoding="utf-8")

    exported = read_export(exported_file)

    assert exported.header == ("Particulars", "No. of vouchers", "Taxable Value", "Tax Amount")
    assert exported.figure("Taxable Sales", "Taxable Value") == Decimal("1444.00")
    assert exported.figure("Nil Rated", "Tax Amount") == Decimal(0)
    assert exported.has_row("Nil Rated")
    with pytest.raises(ExportRowNotFoundError):
        exported.figure("Exports", "Taxable Value")


PURCHASE_HTML = """
<input formcontrolname="ledgerName"><input formcontrolname="entryNo" id="inv">
<input id="txtisInvoiceDate7"
  onkeydown="if(event.key==='Enter')document.getElementById('txt-tmp_barcode-0').hidden=false">
<input id="txt-tmp_barcode-0" hidden onkeydown="if(event.key==='Enter')picker.hidden=false">
<input id="txt-tmp_barcode-1" hidden>
<div id="picker" hidden><input id="searchItems" oninput="hit.hidden=false"
  onkeydown="if(event.key==='Enter'){win.hidden=false;document.getElementById('BarCode-0').focus()}">
  <div id="hit" hidden class="ag-row ag-row-selected"><div col-id="Product">Barcdoe</div></div></div>
<ngb-modal-window id="win" hidden><div class="ag-row" row-index="0">
  <div class="ag-cell"><input id="BarCode-0"></div><div class="ag-cell"><input id="mid1"></div>
  <div class="ag-cell"><input id="txt-qty-0"></div>
  <div class="ag-cell" col-id="amount"></div>
  <div class="ag-cell" col-id="purchaseRate" id="rate-cell">80.000</div>
  <div class="ag-cell" id="rate-editor" hidden><input id="txt-purchaseRate-0"></div></div></ngb-modal-window>
<script>
document.getElementById('inv').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('txtisInvoiceDate7').focus(); });
const order = ['BarCode-0', 'mid1', 'txt-qty-0'];
document.addEventListener('keydown', e => {
  const at = order.indexOf(document.activeElement.id);
  if (e.key === 'Tab' && at >= 0 && at < order.length - 1) {
    e.preventDefault(); document.getElementById(order[at+1]).focus(); }
  if (e.key === 'F10') document.getElementById('txt-tmp_barcode-1').hidden = false; });
document.getElementById('txt-qty-0').addEventListener('keydown', e => {
  if (e.key === 'Tab') { e.preventDefault();
    document.querySelector('[col-id=amount]').textContent = (e.target.value * 80).toFixed(3);
    document.getElementById('txt-qty-0').blur(); } });
document.getElementById('rate-cell').addEventListener('dblclick', () => {
  document.getElementById('rate-editor').hidden = false;
  document.getElementById('txt-purchaseRate-0').focus(); });
document.getElementById('txt-purchaseRate-0').addEventListener('keydown', e => {
  if (e.key === 'Tab') { e.preventDefault();
    document.getElementById('rate-cell').textContent = Number(e.target.value).toFixed(3); } });
</script>
"""


def test_purchase_page_enters_invoice_number_and_one_garments_line(site: Page) -> None:
    site.route(
        f"{SITE}/purchase-stub",
        lambda r: r.fulfill(body=PURCHASE_HTML, content_type="text/html; charset=utf-8"),
    )
    site.goto("/purchase-stub")
    purchase = PurchaseBillPage(site)

    purchase.enter_invoice_number_and_date("778899")
    purchase.add_garments_line(0, GarmentsPurchaseLine("Barcdoe", Decimal(3), Decimal(50)))

    expect(site.locator("#inv")).to_have_value("778899")
    expect(site.locator("#txt-qty-0")).to_have_value("3")
    expect(site.locator("#txt-purchaseRate-0")).to_have_value("50")
