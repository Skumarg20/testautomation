"""Offline checks of the sale, purchase, report and master page fixes from the 2026-10 code review.

Each check runs a page object against a small HTML stub or a fake; no MargBooks app is needed.
"""

from decimal import Decimal
from typing import Any, cast

import pytest
from playwright.sync_api import Page, expect

from pages.components.whole_text import whole_text
from pages.purchase.documents import invoice_footer
from pages.purchase.documents.invoice_footer import InvoiceFooter
from pages.purchase.documents.item_stock import ItemStock, StockReadError, stock_quantity
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.racks import rack_records
from pages.racks.rack_records import RackRecords
from pages.reports.accounting_reports import TrialBalancePage
from pages.sale.chemist.ledger_editor import LedgerEditor
from pages.sale.chemist.rate_validation_page import RateValidationPage
from pages.sale.chemist.sale_bill_page import SaleBillPage
from pages.sale.documents import bill, header, invoice_totals, item_grid, screen
from pages.sale.documents import selection_window as sale_selection
from pages.sale.documents import stock as sale_stock
from pages.sale.documents.bill import SaleBillDocument, SaveNotStartedError
from pages.sale.documents.document_requests import Person, ProductLine
from pages.sale.documents.flows import stored_case
from pages.sale.documents.header import DocumentHeader
from pages.sale.documents.invoice_totals import InvoiceTotals
from pages.sale.documents.item_grid import FIRST_DISCOUNT, DocumentItemGrid
from pages.sale.documents.pending_windows import PendingWindows
from pages.sale.documents.stock import StockLedger, StockSnapshot

pytestmark = pytest.mark.framework

QUICK_MS = 1_000
SHORT_MS = 300


@pytest.fixture
def quick(page: Page, monkeypatch: pytest.MonkeyPatch) -> Page:
    """A blank page with short waits: the stubs answer at once, so long timeouts only slow failures."""
    page.set_default_timeout(QUICK_MS)
    monkeypatch.setattr(screen, "DIALOG_WAIT_MS", 100)
    monkeypatch.setattr(sale_selection, "WINDOW_WAIT_MS", 100)
    return page


def _sale_totals(gross: str, taxes: dict[str, str], invoice_value: str) -> str:
    tax_boxes = "".join(
        f'<div><div>{name}</div><div><span class="blueColor">{amount}</span></div></div>'
        for name, amount in taxes.items()
    )
    return (
        '<div ref="eBodyContainer"></div>'
        f'<div ref="eBodyContainer"><div row-id="0"><div col-id="DisplayAmount">{gross}</div></div></div>'
        f'{tax_boxes}<div class="bill-value-text">Invoice Value {invoice_value}</div>'
    )


# R052: a totals cell that never renders fails the invoice check instead of switching it off.
def test_sale_invoice_check_fails_when_the_gross_total_never_shows(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(invoice_totals, "GROSS_TIMEOUT_MS", SHORT_MS)
    quick.set_content(
        '<div ref="eBodyContainer"></div><div class="bill-value-text">Invoice Value 500.00</div>'
    )

    with pytest.raises(AssertionError):
        InvoiceTotals(quick).expect_consistent(has_lines=True)


# R052: a gross of 0.00 on a document with lines is compared, not taken as "no lines".
def test_sale_invoice_check_compares_a_zero_gross_when_the_document_has_lines(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(invoice_totals, "FIGURE_WAIT_MS", 100)
    quick.set_content(_sale_totals("0.00", {}, "118.00"))

    with pytest.raises(invoice_totals.InvoiceTotalMismatchError):
        InvoiceTotals(quick).expect_consistent(has_lines=True)


# R052: only a document the caller says has no lines skips the check.
def test_sale_invoice_check_is_skipped_only_for_a_document_without_lines(quick: Page) -> None:
    quick.set_content("<p>no totals at all</p>")

    InvoiceTotals(quick).expect_consistent(has_lines=False)


# R052: the purchase copy compares a zero gross too.
def test_purchase_invoice_check_compares_a_zero_gross(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(invoice_footer, "OPTIONAL_TIMEOUT_MS", 100)
    quick.set_content(
        '<div class="ag-body-container"></div>'
        '<div class="ag-body-container"><div row-id="0"><div col-id="DisplayAmount">0.00</div></div></div>'
        '<span class="rb">Total Disc : 0.00</span>'
        '<div class="pr-0 bill-value-text">Invoice Value 118.00</div>'
    )

    with pytest.raises(invoice_footer.InvoiceMismatchError):
        InvoiceFooter(quick).expect_invoice_value_consistent()


# R059: an inter-state sale carries IGST instead of CGST and SGST.
def test_sale_invoice_check_counts_igst(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(invoice_totals, "FIGURE_WAIT_MS", 100)
    quick.set_content(_sale_totals("100.00", {"IGST": "18.00"}, "118.00"))

    InvoiceTotals(quick).expect_consistent(has_lines=True)


# R059: the purchase copy of the check, for an inter-state purchase.
def test_purchase_invoice_check_counts_igst(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(invoice_footer, "OPTIONAL_TIMEOUT_MS", 100)
    quick.set_content(
        '<div class="ag-body-container"></div>'
        '<div class="ag-body-container"><div row-id="0"><div col-id="DisplayAmount">100.00</div></div></div>'
        '<span class="rb">Total Disc : 0.00</span>'
        '<div><div>IGST Input</div><div><span class="blueColor">18.00</span></div></div>'
        '<div class="pr-0 bill-value-text">Invoice Value 118.00</div>'
    )

    InvoiceFooter(quick).expect_invoice_value_consistent()


SAVED_BILLS_HTML = """
<button id="btn-Close">Close</button>
<div id="search-dialog" hidden>
  <button id="btnYes" onclick="document.getElementById('list').hidden = false">Yes</button>
  <div id="list" hidden>
    <input type="search" aria-label="Search">
    <div role="row" tabindex="0" class="row"><div col-id="entryNo"><span>112</span></div></div>
    <div role="row" tabindex="0" class="row"><div col-id="entryNo"><span>12</span></div></div>
  </div>
</div>
<input formcontrolname="entryNo">
<button class="blue-btn btn">Modify</button>
<script>
  let selected = document.querySelector('.row');
  document.querySelectorAll('.row').forEach(row => row.addEventListener('click', () => { selected = row; }));
  document.addEventListener('keydown', event => {
    const dialog = document.getElementById('search-dialog');
    if (event.altKey && event.key.toLowerCase() === 'm') dialog.hidden = false;
    if (event.key === 'Enter' && selected) {
      document.querySelector('[formcontrolname="entryNo"]').value = selected.textContent.trim();
    }
  });
</script>
"""


# R053: the bill reopened for modification is the searched one, not whichever row had focus.
def test_reopen_for_modification_opens_the_bill_searched_for(quick: Page) -> None:
    quick.set_content(SAVED_BILLS_HTML)

    SaleBillPage(quick).reopen_for_modification("12")

    expect(quick.locator('[formcontrolname="entryNo"]')).to_have_value("12")


ITEM_MASTER_HTML = """
<input id="controlRoomSearchField">
<div role="row"><div role="gridcell">Amoxicillin Plus</div><div role="gridcell"><action><button
  onclick="openItem('Amoxicillin Plus')">Edit</button></action></div></div>
<div role="row"><div role="gridcell">Amoxicillin</div><div role="gridcell"><action><button
  onclick="openItem('Amoxicillin')">Edit</button></action></div></div>
<div id="form" hidden><input id="txtProduct"><input formcontrolname="ratea">
  <button id="btnSave" onclick="save()">Save</button></div>
<div id="toasts"></div>
<script>
  window.saved = {};
  function openItem(name) {
    document.getElementById('form').hidden = false;
    document.getElementById('txtProduct').value = name;
  }
  function save() {
    window.saved[document.getElementById('txtProduct').value] =
      document.querySelector('[formcontrolname="ratea"]').value;
    document.getElementById('toasts').innerHTML = '<notifier-notification '
      + 'class="notifier__notification--success">record updated successfully</notifier-notification>';
  }
</script>
"""


# R054: the rate is written to the item named, not to the first row of the unfiltered list.
def test_change_item_rate_edits_the_named_item_only(quick: Page) -> None:
    quick.set_content(ITEM_MASTER_HTML)

    RateValidationPage(quick).change_item_rate("Amoxicillin", "a", Decimal("12.50"))

    assert quick.evaluate("window.saved") == {"Amoxicillin": "12.50"}


# R055: a discount the case asks for fails loudly when its cell cannot be reached.
def test_discount_that_cannot_be_reached_fails(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(item_grid, "CELL_WAIT_MS", 100)
    monkeypatch.setattr(item_grid, "CELL_TIMEOUT_MS", SHORT_MS)
    quick.set_content('<div ref="eBodyContainer" class="ag-body-viewport"><div row-id="0"></div></div>')

    with pytest.raises(AssertionError):
        DocumentItemGrid(quick).enter_discount(0, FIRST_DISCOUNT, Decimal(5))


# R055: a zero discount needs no cell at all.
def test_zero_discount_is_not_entered(quick: Page) -> None:
    quick.set_content('<div ref="eBodyContainer"><div row-id="0"></div></div>')

    DocumentItemGrid(quick).enter_discount(0, FIRST_DISCOUNT, Decimal(0))


# R055: a batch the case names fails loudly when the batch cell is missing.
def test_named_batch_that_cannot_be_reached_fails(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(item_grid, "CELL_WAIT_MS", 100)
    monkeypatch.setattr(item_grid, "CELL_TIMEOUT_MS", SHORT_MS)
    quick.set_content('<div ref="eBodyContainer"><div row-id="0"></div></div>')

    with pytest.raises(AssertionError):
        DocumentItemGrid(quick).choose_batch(0, "B-1")


# R056: a stock figure that is not a plain number is an error, not zero (sale and purchase share the reader).
@pytest.mark.parametrize("shown", ["10:5", "n/a"])
def test_sale_stock_figure_that_is_not_a_number_is_an_error(shown: str) -> None:
    with pytest.raises(StockReadError):
        stock_quantity("3", shown)


def test_sale_stock_reads_the_empty_figure_as_zero() -> None:
    assert stock_quantity("3", "0:0") == Decimal(0)
    assert sale_stock.StockReadError is StockReadError


PENDING_HTML = """
<div class="ag-row-position-absolute"><span class="ag-icon-checkbox-unchecked"
  onclick="window.ticked.push('other grid 12')">o</span><span>12</span></div>
<pending-challan><h5>Pending Orders</h5><input id="SearchBox">
  <div class="ag-row-position-absolute"><span class="ag-icon-checkbox-unchecked"
    onclick="window.ticked.push('112')">o</span><span>112</span></div>
  <div class="ag-row-position-absolute"><span class="ag-icon-checkbox-unchecked"
    onclick="window.ticked.push('12')">o</span><span>12</span></div>
  <button onclick="this.closest('pending-challan').hidden = true">Save</button>
</pending-challan>
<script>window.ticked = [];</script>
"""


# R057: the earlier document is ticked by its exact number, inside its own window.
def test_pending_document_is_ticked_by_exact_number_in_its_window(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(PendingWindows, "_select_every_item", lambda _self: None)
    quick.set_content(PENDING_HTML)

    PendingWindows(quick)._pull_from("Order", "12")

    assert quick.evaluate("window.ticked") == ["12"]


ITEMS_DRAWN_LATE_HTML = """
<challanorder-item><div class="ag-header-select-all"><span class="ag-icon" onclick="toggle()">all</span></div>
  <div id="rows"></div>
  <button onclick="this.closest('challanorder-item').hidden = true">Save</button></challanorder-item>
<script>
  window.allTicked = false;
  function draw() {
    const box = document.querySelector('.ag-header-select-all');
    box.querySelectorAll('.ag-checkbox-checked').forEach(el => el.remove());
    if (window.allTicked) box.insertAdjacentHTML('beforeend', '<span class="ag-checkbox-checked">v</span>');
  }
  function toggle() { window.allTicked = !window.allTicked; draw(); }
  setTimeout(() => {
    document.getElementById('rows').innerHTML = '<div class="ag-row">item</div>';
    window.allTicked = true;
    draw();
  }, 300);
</script>
"""


# R058: rows drawn late and already ticked stay ticked; the select-all box is not clicked blind.
def test_items_drawn_late_and_already_ticked_stay_ticked(quick: Page) -> None:
    quick.set_content(ITEMS_DRAWN_LATE_HTML)

    screen.tick_every_row(quick.locator("challanorder-item"))

    assert quick.evaluate("window.allTicked") is True


# R058: rows that are not ticked are ticked by the select-all box.
def test_items_not_yet_ticked_are_ticked(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(screen, "TICKED_LOOKUP_MS", 100)
    quick.set_content(ITEMS_DRAWN_LATE_HTML.replace("window.allTicked = true;", ""))

    screen.tick_every_row(quick.locator("challanorder-item"))

    assert quick.evaluate("window.allTicked") is True


# R060: a patient the case names is not dropped when the field is missing.
def test_named_patient_fails_when_the_field_never_shows(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(header, "FIELD_TIMEOUT_MS", SHORT_MS)
    quick.set_content("<p>no patient field</p>")

    with pytest.raises(AssertionError):
        DocumentHeader(quick).choose_patient(Person("9999999999", "CASH Patient"))


# R163: the save loop stops once the Mode Of Payment window has the focus.
def test_bill_save_stops_when_the_payment_window_takes_focus(quick: Page) -> None:
    quick.set_content(
        '<input id="grid-editor" autofocus>'
        '<ngb-modal-window hidden>Mode Of Payment<input id="txt-amount-0"></ngb-modal-window>'
        "<script>window.ends = 0; document.addEventListener('keydown', event => {"
        " if (event.key !== 'End') return; window.ends += 1;"
        " const modal = document.querySelector('ngb-modal-window'); modal.hidden = false;"
        " document.getElementById('txt-amount-0').focus(); });</script>"
    )
    quick.locator("#grid-editor").focus()

    SaleBillDocument(quick).save()

    assert quick.evaluate("window.ends") == 1


# R163: a save that never leaves the grid is an error, not a silent return.
def test_bill_save_fails_when_focus_never_leaves_the_grid(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bill, "SAVE_ATTEMPTS", 3)
    quick.set_content('<input id="grid-editor">')
    quick.locator("#grid-editor").focus()

    with pytest.raises(SaveNotStartedError, match="grid-editor"):
        SaleBillDocument(quick).save()


class _FakeList:
    def __init__(self, listed: set[str], refused: set[str], log: list[str]) -> None:
        self._listed = listed
        self._refused = refused
        self._log = log

    def open(self) -> None: ...

    def is_listed(self, name: str) -> bool:
        return name in self._listed

    def delete(self, name: str) -> None:
        self._log.append(name)
        if name in self._refused:
            raise AssertionError(f"{name} cannot be deleted")
        self._listed.discard(name)


# R164: one failing rack delete does not stop the store deletes; every leftover is named at the end.
def test_rack_cleanup_runs_every_delete_and_names_each_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    racks = _FakeList({"R1", "R2"}, {"R1"}, log)
    stores = _FakeList({"S1"}, set(), log)
    monkeypatch.setattr(rack_records, "RackList", lambda _page: racks)
    monkeypatch.setattr(rack_records, "StoreList", lambda _page: stores)
    records = RackRecords(cast(Any, None), cast(Any, None))
    for name in ("R1", "R2"):
        records.own_rack_name(name)
    records.own_store_name("S1")

    with pytest.raises(AssertionError, match="R1"):
        records.delete_all()

    assert "R2" in log
    assert "S1" in log


# R165: a report row is the one whose name cell is exactly the name, not one that only contains it.
def test_trial_balance_row_is_found_by_exact_name(quick: Page) -> None:
    quick.set_content(
        '<div role="grid">'
        '<div role="row"><div role="gridcell">Cash Account</div><div role="gridcell">1.00</div>'
        '<div role="gridcell"></div></div>'
        '<div role="row"><div role="gridcell">Cash</div><div role="gridcell">250.00</div>'
        '<div role="gridcell"></div></div></div>'
    )

    assert TrialBalancePage(quick).balance_of("Cash").debit == Decimal("250.00")


# R162: the ledger is opened by its exact name.
def test_ledger_editor_opens_the_ledger_named_exactly(quick: Page) -> None:
    quick.set_content(
        '<input id="SearchBox">'
        '<div role="row"><div col-id="LedgerName">Cash Account</div><div col-id="1">'
        '<button class="mksBtn edit" onclick="window.opened = \'Cash Account\'">e</button></div></div>'
        '<div role="row"><div col-id="LedgerName">Cash</div><div col-id="1">'
        '<button class="mksBtn edit" onclick="window.opened = \'Cash\'">e</button></div></div>'
    )

    LedgerEditor(quick).open_ledger("Cash")

    assert quick.evaluate("window.opened") == "Cash"


def _line(product: str, quantity: str) -> ProductLine:
    return ProductLine(product=product, batch="", quantity=Decimal(quantity), price=Decimal(1))


# R168: two lines of the same product move its stock by their sum.
def test_sale_stock_expectation_adds_up_lines_of_the_same_product(monkeypatch: pytest.MonkeyPatch) -> None:
    checked: list[tuple[str, Decimal]] = []
    ledger = StockLedger.__new__(StockLedger)
    monkeypatch.setattr(
        ledger, "_expect_stock", lambda product, expected: checked.append((product, expected))
    )
    snapshot = StockSnapshot({"3": Decimal(10)})

    ledger.expect_sold(snapshot, (_line("3", "2"), _line("3", "1")))

    assert checked == [("3", Decimal(7))]


# R168: the purchase copy, counting free goods.
def test_purchase_stock_expectation_adds_up_lines_of_the_same_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[tuple[str, Decimal]] = []
    stock = ItemStock.__new__(ItemStock)
    monkeypatch.setattr(stock, "_expect", lambda code, expected: checked.append((code, expected)))
    line = PurchaseLineItem(product="3", quantity=Decimal(2), free=Decimal(1))

    stock.expect_received((line, line), {"3": Decimal(10)})

    assert checked == [("3", Decimal(16))]


# R171: a stored case the workbook no longer has is named in the error.
def test_missing_stored_case_is_named() -> None:
    with pytest.raises(LookupError, match="TC_NOPE"):
        stored_case("bill", "TC_NOPE")


# R162/R165: a multi-word name shown with non-breaking spaces still matches as a whole, and only as a whole.
def test_whole_text_matches_a_name_shown_with_non_breaking_spaces(quick: Page) -> None:
    quick.set_content(
        '<div role="gridcell">Special&nbsp;Discount</div><div role="gridcell">Special&nbsp;Discount 2</div>'
    )

    expect(quick.get_by_role("gridcell").filter(has_text=whole_text("Special Discount"))).to_have_count(1)


# R165: the report row of a multi-word ledger is found when the grid shows it with &nbsp;.
def test_trial_balance_row_is_found_for_a_name_with_non_breaking_spaces(quick: Page) -> None:
    quick.set_content(
        '<div role="grid">'
        '<div role="row"><div role="gridcell">Special&nbsp;Discount</div><div role="gridcell">75.00</div>'
        '<div role="gridcell"></div></div></div>'
    )

    assert TrialBalancePage(quick).balance_of("Special Discount").debit == Decimal("75.00")


# R162: the ledger editor finds a multi-word ledger shown with &nbsp;.
def test_ledger_editor_opens_a_ledger_shown_with_non_breaking_spaces(quick: Page) -> None:
    quick.set_content(
        '<input id="SearchBox">'
        '<div role="row"><div col-id="LedgerName">Ledger&nbsp;Master&nbsp;Discount</div><div col-id="1">'
        '<button class="mksBtn edit" onclick="window.opened = true">e</button></div></div>'
    )

    LedgerEditor(quick).open_ledger("Ledger Master Discount")

    assert quick.evaluate("window.opened") is True
