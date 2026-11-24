"""Offline checks of page-object fixes from the 2026-10 code review, against small HTML stubs and fakes."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest
from playwright.sync_api import BrowserContext, Page, Route, expect

from pages.accounting import loader, receipt_payment_voucher, toasts, voucher_screen
from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.ledger_balances import LedgerBalances
from pages.accounting.list_screen import ListScreen
from pages.accounting.outstanding import credit_desks
from pages.accounting.outstanding.credit_desks import ReceiptDesk
from pages.accounting.owned_ledgers import OwnedLedgers
from pages.accounting.receipt_page import ReceiptPage
from pages.accounting.receipt_payment_voucher import ReceiptPaymentVoucher, VoucherNumberHiddenError
from pages.accounting.two_sided_voucher import TwoSidedVoucher
from pages.accounting.voucher_cases import Leg, SingleSidedCase, TwoSidedCase
from pages.accounting.voucher_flows import SingleSidedFlow, TwoSidedFlow
from pages.accounting.voucher_screen import UnverifiedDeleteError
from pages.auth.dispatch_guard import DispatchGuard
from pages.banking.grid_rows import GridRows
from pages.communication_setup.outbound_guard import OutboundGuard, OutboundRequestAttemptedError
from pages.components import bill_totals
from pages.components.bill_totals import BillTotals
from pages.components.downloads import collect_downloads
from pages.components.send_guard import SendAttemptedError, SendGuard
from pages.components.undo import UndoIncompleteError, undo_all
from pages.dashboard_page import DashboardPage, NotAuthorizedPageError
from pages.grid.chemist_sale_grid import grid_text
from pages.notifications_export.delivery_endpoints import DELIVERY_OR_GLOBAL_WRITE
from pages.print_templates.owned_templates import OwnedTemplates
from pages.purchase.documents import entry_grid
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.entry_grid import EntryGrid
from pages.purchase.documents.feedback import AppFeedback
from pages.sale.documents.selection_window import SelectionWindow

pytestmark = pytest.mark.framework

QUICK_MS = 1_000
LOCAL_SITE = "http://localhost:4200"


def _stub_site(route: Route) -> None:
    route.fulfill(body="<p>stub</p>", content_type="text/html")


@pytest.fixture
def quick(page: Page, monkeypatch: pytest.MonkeyPatch) -> Page:
    """A blank page with short waits: the stubs answer at once, so long timeouts only slow failures."""
    page.set_default_timeout(QUICK_MS)
    monkeypatch.setattr(loader, "APPEAR_TIMEOUT_MS", 100)
    monkeypatch.setattr(toasts, "DISMISS_LOOKUP_MS", 100)
    return page


# R050: the purchase confirmation's Yes and No buttons are both named "Close".
def test_purchase_confirmation_presses_yes_although_both_buttons_are_named_close(quick: Page) -> None:
    quick.set_content(
        '<div class="active modal-new">'
        '<button id="btnYes" aria-label="Close" onclick="document.title=\'yes\'">Yes</button>'
        '<button id="btnNo" aria-label="Close" onclick="document.title=\'no\'">No</button></div>'
    )

    AppFeedback(quick).confirm_if_asked()

    expect(quick).to_have_title("yes")


# R048: a prefilled editor value is replaced, not appended to.
def test_purchase_rate_and_free_replace_the_value_the_editor_opens_with(quick: Page) -> None:
    quick.set_content(
        '<div class="ag-body-container"><div row-id="0">'
        '<div col-id="salePurchaseRate"><input value="50.00"></div>'
        '<div col-id="free"><input value="0"></div></div></div>'
    )
    grid = EntryGrid(quick)

    grid.enter_rate(0, Decimal("100"))
    grid.enter_free(0, Decimal("2"))

    expect(quick.locator('[col-id="salePurchaseRate"] input')).to_have_value("100")
    expect(quick.locator('[col-id="free"] input')).to_have_value("2")


# R155: a rate that differs from the item's asks "Update Change Rate"; the test never stores it on the item.
def test_purchase_rate_change_is_not_stored_on_the_item(quick: Page) -> None:
    quick.set_content(
        '<div class="ag-body-container"><div row-id="0"><div col-id="salePurchaseRate">'
        "<input onkeydown=\"if(event.key==='Enter')ask.hidden=false\"></div></div></div>"
        '<ngb-modal-window id="ask" role="dialog" hidden>Update Change Rate'
        "<button onclick=\"ask.hidden=true;document.title='not stored'\">Don't Store</button>"
        "<button onclick=\"document.title='stored'\">Special Rate</button></ngb-modal-window>"
    )

    EntryGrid(quick).enter_rate(0, Decimal("100"))

    expect(quick).to_have_title("not stored")
    expect(quick.locator("#ask")).to_be_hidden()


# R049: a total row that never shows fails instead of switching the invoice check off.
def test_purchase_gross_amount_fails_when_the_total_row_never_shows(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entry_grid, "TOTAL_TIMEOUT_MS", 300, raising=False)
    quick.set_content('<div class="ag-body-container"></div><div class="ag-body-container"></div>')

    with pytest.raises(AssertionError):
        EntryGrid(quick).gross_amount()


# R051: the check waits for the screen or the not-authorized page, whichever renders first.
def test_page_open_check_fails_when_the_not_authorized_page_renders_late(quick: Page) -> None:
    quick.set_content(
        "<h1>Loading</h1><script>setTimeout(() => { document.body.innerHTML ="
        " '<error-page><h1>Oops! You are not authorized.</h1></error-page>'; }, 500)</script>"
    )
    users = quick.get_by_role("heading", name="Users")

    with pytest.raises(NotAuthorizedPageError):
        DashboardPage(quick).expect_page_open("blank", users)


def test_page_open_check_passes_once_the_screen_renders_late(quick: Page) -> None:
    quick.set_content(
        "<h1>Loading</h1><script>setTimeout(() => { document.body.innerHTML = '<h1>Users</h1>'; }, 500)"
        "</script>"
    )

    DashboardPage(quick).expect_page_open("blank", quick.get_by_role("heading", name="Users"))


# R151: the outbound guard matches on the path, so a localhost target is guarded too.
def test_outbound_guard_aborts_a_template_save_on_a_localhost_target(
    context: BrowserContext, page: Page
) -> None:
    context.route(f"{LOCAL_SITE}/**", _stub_site)
    guard = OutboundGuard(page)
    guard.arm()
    page.goto(f"{LOCAL_SITE}/communication")

    page.evaluate("fetch('/api/template/save', {method: 'POST'}).catch(() => null)")

    with pytest.raises(OutboundRequestAttemptedError):
        guard.expect_nothing_sent()


def test_outbound_guard_lets_reads_through(context: BrowserContext, page: Page) -> None:
    context.route(f"{LOCAL_SITE}/**", _stub_site)
    guard = OutboundGuard(page)
    guard.arm()
    page.goto(f"{LOCAL_SITE}/communication")

    status = page.evaluate("fetch('/api/sms/templates').then(response => response.status)")

    assert status == 200
    guard.expect_nothing_sent()


# R158: the guards cover every tab of the test's context, not only the page they were armed on.
def test_delivery_guard_covers_a_tab_the_app_opens(context: BrowserContext, page: Page) -> None:
    context.route(f"{LOCAL_SITE}/**", _stub_site)
    guard = SendGuard(page, DELIVERY_OR_GLOBAL_WRITE)
    guard.arm()
    tab = context.new_page()
    tab.goto(f"{LOCAL_SITE}/report.pdf")

    tab.evaluate("fetch('/api/Template/SendEmailPdfExcel', {method: 'POST'}).catch(() => null)")
    with pytest.raises(SendAttemptedError):
        guard.expect_nothing_sent()


# N5 (J21): the app's service worker answers API calls out of Playwright's sight, so route guards only
# work when every context blocks it.
def test_every_context_blocks_the_service_worker(browser_context_args: dict[str, Any]) -> None:
    assert browser_context_args["service_workers"] == "block"


def test_dispatch_guard_covers_a_tab_the_app_opens(context: BrowserContext, page: Page) -> None:
    context.route(f"{LOCAL_SITE}/**", _stub_site)
    guard = DispatchGuard(page)
    guard.install()
    tab = context.new_page()
    tab.goto(f"{LOCAL_SITE}/register")

    tab.evaluate("fetch('/api/RegisterUser/CheckOTP', {method: 'POST'}).catch(() => null)")

    with pytest.raises(AssertionError):
        guard.expect_nothing_dispatched()


# R152: list cells are matched to their header by col-id, not by position.
def test_grid_row_is_read_by_header_through_the_column_id(quick: Page) -> None:
    quick.set_content(
        '<div role="row"><div role="columnheader" col-id="select"></div>'
        '<div role="columnheader" col-id="party">Party Name</div>'
        '<div role="columnheader" col-id="amount">Amount</div>'
        '<div role="columnheader" col-id="other-grid">Elsewhere</div></div>'
        '<div role="row" id="entry"><div role="gridcell" col-id="amount">100.00</div>'
        '<div role="gridcell" col-id="party">Cash 1</div></div>'
    )

    listed = GridRows(quick).read_by_header(quick.locator("#entry"))

    assert listed == {"Party Name": "Cash 1", "Amount": "100.00"}


# Since V 4.3.599 the list headers carry col-id on a wrapper or an inner element, not on the columnheader.
def test_grid_row_is_read_by_header_when_the_column_id_is_beside_the_header_role(quick: Page) -> None:
    quick.set_content(
        '<div role="row"><div col-id="party"><div role="columnheader">Party Name</div></div>'
        '<div role="columnheader"><span col-id="amount">Amount</span></div></div>'
        '<div role="row" id="entry"><div role="gridcell" col-id="amount">100.00</div>'
        '<div role="gridcell" col-id="party">Cash 1</div></div>'
    )

    listed = GridRows(quick).read_by_header(quick.locator("#entry"))

    assert listed == {"Party Name": "Cash 1", "Amount": "100.00"}


class _FakeToasts:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def expect_warning(self) -> None:
        self._calls.append("expect_warning")


class _RefusingFirstAccount:
    """A two-sided screen whose first account is refused with a warning."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.toasts = _FakeToasts(self.calls)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def record(*_: object) -> None:
            self.calls.append(name)

        return record

    def account_warning_shown(self) -> bool:
        return True

    def voucher_number(self) -> str:
        self.calls.append("voucher_number")
        return "1"


# R045: a refusal of the first account ends a negative case, as for the second account.
def test_two_sided_negative_case_stops_when_the_first_account_is_refused() -> None:
    screen = _RefusingFirstAccount()
    case = TwoSidedCase(
        id="JV-X",
        is_negative=True,
        day=date.today(),
        first=Leg("debit", "Refused Ledger", "100"),
        second=Leg("credit", "Cash Account", "100"),
        narration="",
        delete_after=False,
    )

    TwoSidedFlow(cast(TwoSidedVoucher, screen), case).run()

    assert "expect_warning" in screen.calls
    assert not {"enter_leg_amount", "save", "expect_rejected"} & set(screen.calls)


# R046: single-sided balance checks read the refreshed balance, not the cached one.
def test_ledger_balance_is_read_after_single_ledger_refresh(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(AccountingMenu, "open_ledger_list", lambda _self: None)
    quick.set_content(
        '<input id="SearchBox"><div role="row"><div role="gridcell">Party A</div>'
        '<div col-id="0">100.00 Dr</div></div>'
        '<button title="Single Ledger Refresh" onclick="refresh()">R</button><div id="toasts"></div>'
        "<script>function refresh() {"
        " document.querySelector('[col-id=\"0\"]').textContent = '250.00 Dr';"
        " document.getElementById('toasts').innerHTML ="
        " '<notifier-notification class=\"notifier__notification--success\">Done</notifier-notification>';"
        " setTimeout(() => { document.getElementById('toasts').innerHTML = ''; }, 200); }</script>"
    )

    assert LedgerBalances(quick).balance_of("Party A") == Decimal("250.00")


class _FakeReceipt:
    def enter_row_date(self, _day: date) -> None: ...

    def enter_amount(self, _amount: str) -> None: ...

    def voucher_number(self) -> str:
        return "0000069"  # provisional: another save took it


class _FakeLedgerReport:
    listed: list[str] = []

    def __init__(self, _page: Page) -> None: ...

    def voucher_numbers(self, _ledger: str, voucher_type: str) -> list[str]:
        assert voucher_type == "Receipt"
        return list(self.listed)


# R005: a receipt's number is read back after the save, not taken from the unsaved form.
def test_receipt_desk_returns_the_number_the_receipt_was_saved_under(
    page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(credit_desks, "LedgerReportPage", _FakeLedgerReport)
    for step in ("_start_for", "_adjust_from_short_amount", "_save"):
        monkeypatch.setattr(ReceiptDesk, step, lambda *_: None)
    desk = ReceiptDesk(page)
    monkeypatch.setattr(desk, "_receipt", _FakeReceipt())

    _FakeLedgerReport.listed = ["0000070"]
    first = desk.create("Party A", Decimal(100), {})
    _FakeLedgerReport.listed = ["0000070", "0000072"]
    second = desk.create("Party A", Decimal(50), {})

    assert (first, second) == ("0000070", "0000072")


def test_receipt_desk_refuses_to_guess_between_two_new_receipts(
    page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(credit_desks, "LedgerReportPage", _FakeLedgerReport)
    for step in ("_start_for", "_adjust_from_short_amount", "_save"):
        monkeypatch.setattr(ReceiptDesk, step, lambda *_: None)
    desk = ReceiptDesk(page)
    monkeypatch.setattr(desk, "_receipt", _FakeReceipt())
    _FakeLedgerReport.listed = ["0000070", "0000071"]

    with pytest.raises(AssertionError):
        desk.create("Party A", Decimal(100), {})


# R044: reading the number is a query; it never switches the tenant-wide setting.
def test_hidden_voucher_number_is_reported_without_changing_the_tenant(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(receipt_payment_voucher, "NUMBER_LOOKUP_MS", 200)
    quick.set_content('<a id="aControlRoomSetting" onclick="document.title=\'changed\'">Control Room</a>')

    with pytest.raises(VoucherNumberHiddenError):
        ReceiptPage(quick).voucher_number()

    assert quick.title() != "changed"


# R043: a voucher that does not book the case's account is not deleted.
def test_delete_voucher_refuses_a_voucher_of_another_account(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(AccountingMenu, "open_screen", lambda *_: None)
    monkeypatch.setattr(ListScreen, "filter_to_this_week", lambda _self: None)
    monkeypatch.setattr(voucher_screen, "OWNER_CHECK_TIMEOUT_MS", 300, raising=False)
    quick.set_content(
        '<input id="SearchBox">'
        '<div role="row"><div role="gridcell" ondblclick="openVoucher()">0000070</div></div>'
        "<script>function openVoucher() { document.body.innerHTML ="
        ' \'<div ref="eBodyContainer"><div row-id="0">'
        '<div col-id="ledgerLinkID">Someone Else</div></div></div>\';'
        " document.addEventListener('keydown', e => {"
        " if (e.key === 'Delete') document.title = 'deleted'; }); }"
        "</script>"
    )

    with pytest.raises(AssertionError):
        ReceiptPage(quick).delete_voucher("0000070", ("Party A",))

    assert quick.title() != "deleted"


class _SingleSidedScreen:
    """A receipt screen that hides the voucher number until the setting is switched on."""

    BALANCE_SIGN = 1

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.toasts = _FakeToasts(self.calls)
        self.ledgers = self

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def record(*_: object) -> None:
            self.calls.append(name)

        return record

    def balance_of(self, _account: str) -> Decimal:
        self.calls.append("balance_of")
        return Decimal(0)

    def shows_voucher_number(self) -> bool:
        self.calls.append("shows_voucher_number")
        return "turn_on_voucher_numbers" in self.calls

    def voucher_number(self) -> str:
        self.calls.append("voucher_number")
        return "1"


# R044: the setting is switched on an open voucher, and the number is read on a voucher opened after it.
def test_single_sided_delete_case_switches_the_setting_on_an_open_voucher() -> None:
    screen = _SingleSidedScreen()
    case = SingleSidedCase(
        id="RC-X",
        is_negative=False,
        day=date.today(),
        leg=Leg("debit", "Party A", "100"),
        short_amount="0",
        narration="",
        delete_after=True,
    )

    SingleSidedFlow(cast(ReceiptPaymentVoucher, screen), case).run()

    calls = screen.calls
    switched = calls.index("turn_on_voucher_numbers")
    assert calls.index("open_new_voucher") < switched
    assert "open_new_voucher" in calls[switched : calls.index("voucher_number")]
    assert calls.index("balance_of") < calls.index("open_new_voucher")


def _open_voucher_page(page: Page, account_cells: str) -> None:
    """A voucher list with one row; opening it shows a voucher booking `account_cells` (HTML cells)."""
    page.set_content(
        '<input id="SearchBox">'
        '<div role="row"><div role="gridcell" ondblclick="openVoucher()">0000070</div></div>'
        "<script>function openVoucher() { document.body.innerHTML ="
        f" '<div ref=\"eBodyContainer\">{account_cells}</div>';"
        " document.addEventListener('keydown', e => {"
        " if (e.key === 'Delete') document.title = 'deleted'; }); }"
        "</script>"
    )


@pytest.fixture
def voucher_list(quick: Page, monkeypatch: pytest.MonkeyPatch) -> Page:
    monkeypatch.setattr(AccountingMenu, "open_screen", lambda *_: None)
    monkeypatch.setattr(ListScreen, "filter_to_this_week", lambda _self: None)
    monkeypatch.setattr(voucher_screen, "OWNER_CHECK_TIMEOUT_MS", 300, raising=False)
    return quick


# R043: the account name must match a whole cell, so "Cash" does not pass on a "Petty Cash" row.
def test_delete_voucher_refuses_a_voucher_whose_account_only_contains_the_name(voucher_list: Page) -> None:
    _open_voucher_page(voucher_list, '<div col-id="ledgerLinkID">Petty Cash</div>')

    with pytest.raises(AssertionError):
        ReceiptPage(voucher_list).delete_voucher("0000070", ("Cash",))

    assert voucher_list.title() != "deleted"


# R043: a two-sided voucher must book both ledgers, not just a shared one.
def test_delete_voucher_refuses_a_voucher_that_books_only_one_of_the_ledgers(voucher_list: Page) -> None:
    _open_voucher_page(voucher_list, '<div col-id="ledgerLinkID">Cash Account</div>')

    with pytest.raises(AssertionError):
        ReceiptPage(voucher_list).delete_voucher("0000070", ("Cash Account", "Party A"))

    assert voucher_list.title() != "deleted"


def test_ownership_check_passes_a_voucher_that_books_every_ledger(quick: Page) -> None:
    quick.set_content(
        '<div ref="eBodyContainer"><div col-id="ledgerLinkID"> Cash Account </div>'
        '<div col-id="ledgerLinkID">Party A</div></div>'
    )

    ReceiptPage(quick)._expect_books_all_of(("Cash Account", "Party A"))


# R043: with no account to check, the voucher is not deleted at all.
def test_delete_voucher_refuses_when_the_case_names_no_account(voucher_list: Page) -> None:
    _open_voucher_page(voucher_list, '<div col-id="ledgerLinkID">Someone Else</div>')

    with pytest.raises(UnverifiedDeleteError):
        ReceiptPage(voucher_list).delete_voucher("0000070", ())

    assert voucher_list.title() != "deleted"


class _StuckTemplates:
    """Template Customize where a delete never takes effect."""

    def __init__(self) -> None:
        self.deletes = 0

    def open_for(self, _voucher_type: str) -> None: ...

    def custom_template_count(self, _name: str) -> int:
        return 1

    def delete_custom(self, _name: str) -> None:
        self.deletes += 1
        if self.deletes > 5:
            raise RuntimeError("delete loop does not end")

    def expect_custom_template_count(self, _name: str, count: int) -> None:
        if count != 1:
            raise AssertionError(f"expected {count} copies, found 1")


# R047: template clean-up is bounded and fails loudly when a delete does not take effect.
def test_template_cleanup_fails_instead_of_looping_when_a_delete_does_not_take(
    page: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    owned = OwnedTemplates(page, "run1")
    owned.new_name()
    screen = _StuckTemplates()
    monkeypatch.setattr(owned, "_screen", screen)

    with pytest.raises(AssertionError):
        owned.delete_all()

    assert screen.deletes <= 2


# R153: teardown runs every undo step and reports every failure.
def test_undo_runs_every_step_and_reports_each_failure() -> None:
    ran: list[str] = []

    def fail(name: str) -> Callable[[], None]:
        def step() -> None:
            ran.append(name)
            raise AssertionError(f"{name} refused")

        return step

    with pytest.raises(UndoIncompleteError) as failure:
        undo_all([("voucher 1", fail("voucher 1")), ("ledger A", lambda: ran.append("ledger A"))])

    assert ran == ["voucher 1", "ledger A"]
    assert "voucher 1" in str(failure.value)


class _FlakyOpeningBalances:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_ledger(self, name: str) -> None:
        if name == "B":
            raise AssertionError("timed out")
        self.deleted.append(name)


def test_owned_ledgers_are_all_deleted_when_one_delete_fails() -> None:
    opening_balances = _FlakyOpeningBalances()
    ledgers = OwnedLedgers(cast(Any, opening_balances))
    ledgers._names.extend(["A", "B"])

    with pytest.raises(UndoIncompleteError):
        ledgers.delete_all()

    assert opening_balances.deleted == ["A"]


# R155: labels made in the same second by one process differ (the counter). Across xdist workers they rely
# on each process's random start, which makes a clash unlikely but not impossible; that is not tested here.
def test_labels_made_in_the_same_second_differ_and_stay_short() -> None:
    first, second = timestamp_label(), timestamp_label()

    assert first != second
    assert len(first) <= len("2026-10-12T10:00:00")


# R156: dialogs Angular left hidden in the DOM do not cost an Escape press.
def test_leaving_a_bill_presses_no_escape_for_hidden_dialogs(
    quick: Page, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bill_totals, "DISCARD_PROMPT_TIMEOUT_MS", 200)
    quick.set_content(
        '<ngb-modal-window aria-hidden="true">old picker</ngb-modal-window>'
        '<button id="btnEsc1" onclick="document.title=\'closed\'">Esc</button>'
        "<script>window.escapes = 0;"
        " document.addEventListener('keydown', e => { if (e.key === 'Escape') window.escapes++; });</script>"
    )

    BillTotals(quick).leave_without_saving()

    assert quick.evaluate("window.escapes") == 0
    expect(quick).to_have_title("closed")


def test_leaving_a_bill_closes_an_open_dialog_first(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bill_totals, "DISCARD_PROMPT_TIMEOUT_MS", 200)
    quick.set_content(
        '<ngb-modal-window id="alert">Alert</ngb-modal-window>'
        '<button id="btnEsc1" onclick="document.title=\'closed\'">Esc</button>'
        "<script>window.escapes = 0; document.addEventListener('keydown', e => {"
        " if (e.key === 'Escape') { window.escapes++; document.getElementById('alert')?.remove(); } });"
        "</script>"
    )

    BillTotals(quick).leave_without_saving()

    assert quick.evaluate("window.escapes") == 1


# R157: money is typed in plain decimal notation, never as a float's exponent form.
@pytest.mark.parametrize(
    ("value", "typed"), [(1e-05, "0.00001"), (Decimal("12.50"), "12.50"), (3, "3"), (0.1, "0.1")]
)
def test_grid_values_are_typed_in_plain_decimal_notation(value: Decimal | float, typed: str) -> None:
    assert grid_text(value) == typed


# R153: a list.append handler breaks Playwright's sync page.on, which tags every handler it wraps.
def test_downloads_that_follow_a_click_are_collected(quick: Page) -> None:
    quick.set_content('<a id="file" download="a.txt" href="data:text/plain,hello">file</a>')
    downloads = collect_downloads(quick)

    with quick.expect_download():
        quick.locator("#file").click()

    assert [download.suggested_filename for download in downloads] == ["a.txt"]


# R154: a product is picked by its item code, so the picker must search the Itemcode column.
def test_product_is_searched_in_the_item_code_mode(quick: Page, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pages.stock.search_typing.KEY_DELAY_MS", 0)
    quick.set_content(
        '<div class="modal-dialog modal-lg"><input type="search" aria-label="Search" id="box">'
        '<select id="mode"><option>Description</option><option>Itemcode</option></select>'
        '<div id="hit" hidden><div col-id="itemcode" class="ag-cell-value" onclick="this.remove()">'
        "44646015</div></div></div>"
        "<script>box.oninput = () => {"
        " hit.hidden = !(mode.value === 'Itemcode' && box.value === '44646015') }</script>"
    )

    SelectionWindow(quick).choose_in_column("itemcode", "44646015")

    expect(quick.locator('[col-id="itemcode"]')).to_have_count(0)


# R156: on the purchase bill End only moves focus onto Save (seen 2026-10-14); the Save button saves.
def test_purchase_entry_save_presses_the_save_button(quick: Page) -> None:
    quick.set_content(
        '<div><label>Invoice No.</label><input value="INV-1"></div>'
        '<input formcontrolname="billDiscountAmount" id="discount">'
        '<button id="btnSave61" onclick="document.title=\'saved\'">F10 / End Save</button>'
        '<button id="btnSaveDraft61" onclick="document.title=\'draft\'">Save as draft</button>'
        "<script>document.addEventListener('keydown', e => {"
        " if (e.key === 'End') document.getElementById('btnSave61').focus() })</script>"
    )
    quick.locator("#discount").focus()

    number = PurchaseBillEntryPage(quick).save()

    assert number == "INV-1"
    expect(quick).to_have_title("saved")
