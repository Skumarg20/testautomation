"""Exploration for the outstanding/advance journey. Delete after planning.

Not read-only: it creates customers, saves sale bills, receipts and a sale return, and deletes bills in the
shared garments tenant. Tests share state through files in PROBE_OUT and assert nothing. Excluded from normal
collection by tests/journeys/conftest.py; run it only by naming this file.
"""
import os
from datetime import date
from pathlib import Path

from pages.accounting.receipt_page import ReceiptPage
from pages.dashboard_page import DashboardPage

OUT = Path(os.environ.get("PROBE_OUT", "/tmp"))


def _dump(page, name):
    (OUT / f"{name}.txt").write_text(page.url + "\n" + page.locator("body").inner_text())
    (OUT / f"{name}.html").write_text(page.content())
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)


def test_receivable_report(page_as):
    page = page_as("garments")
    DashboardPage(page).open()
    page.wait_for_timeout(6000)
    page.get_by_role("link", name="Report").first.click()
    page.wait_for_timeout(8000)
    section = page.locator("text=Receivable").first
    section.locator("xpath=following::*[normalize-space(text())='Ledger Wise'][1]").click()
    page.wait_for_timeout(12000)
    _dump(page, "receivable_filter")
    page.keyboard.press("Enter")
    page.wait_for_timeout(8000)
    page.get_by_text("Arun Sharma", exact=True).first.dblclick()
    page.wait_for_timeout(10000)
    _dump(page, "receivable_billwise")
    page.keyboard.press("Enter")
    page.wait_for_timeout(8000)
    _dump(page, "receivable_billwise_enter")


def test_receipt_adjust_window(page_as):
    page = page_as("garments")
    DashboardPage(page).open()
    receipt = ReceiptPage(page)
    receipt.open_new_voucher()
    receipt.choose_mode("Cash Account")
    receipt.select_account(0, "Ajay")
    receipt.enter_row_date(date.today())
    receipt.enter_amount("1")
    page.wait_for_timeout(3000)
    _dump(page, "receipt_after_amount")
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    _dump(page, "receipt_after_enter")


def test_sale_bill_save_window(page_as):
    from pages.sale.documents.bill import SaleBillDocument

    page = page_as("garments")
    DashboardPage(page).open()
    bill = SaleBillDocument(page)
    bill.open_new()
    bill.choose_party("Ajay")
    _dump(page, "bill_after_party")
    cell = bill.grid.cell(0, "itemLinkID")
    cell.click()
    page.keyboard.press("Enter")
    page.wait_for_timeout(6000)
    _dump(page, "item_picker")
    search = page.locator("div.modal-dialog.modal-lg").get_by_role("searchbox")
    search.press_sequentially("Sample", delay=150)
    page.wait_for_timeout(5000)
    _dump(page, "item_picker_sample")
    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
    _dump(page, "after_item_enter")
    for k in range(4):
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
    _dump(page, "after_more_enters")
    bill.save()
    page.wait_for_timeout(6000)
    _dump(page, "bill_save_window")


def test_tax_categories(page_as):
    from pages.inventory.create_item_page import CreateItemPage, LookupField

    page = page_as("garments")
    DashboardPage(page).open()
    form = CreateItemPage(page)
    form.open()
    form.enter_product("probe-unsaved")
    form._choose_suggestion(LookupField.UNIT, "PCS")
    form.change_hsn("12345678")
    _dump(page, "item_form_after_hsn")
    for text in ["GST", "Sale", "0", "Exem", "Nil", "Non"]:
        form._type_into(LookupField.TAX_CATEGORY, text)
        page.wait_for_timeout(4000)
        opts = page.get_by_role("listbox").get_by_role("option").all_inner_texts()
        with open(OUT / "tax_categories.txt", "a") as fh:
            fh.write(f"{text}: {opts}\n")


def test_flow_with_new_party(page_as, run_id):
    from pages.accounting.receipt_page import ReceiptPage
    from pages.masters.master_records import MasterRecords
    from pages.sale.documents.bill import SaleBillDocument
    from test_data.masters import MasterDataFactory

    page = page_as("garments")
    DashboardPage(page).open()
    party = MasterRecords(page, MasterDataFactory(run_id)).saved_customer()
    (OUT / "flow_party.txt").write_text(party.name)
    try:
        DashboardPage(page).open()
        bill = SaleBillDocument(page)
        bill.open_new()
        bill.choose_party(party.name)
        bill.grid.cell(0, "itemLinkID").click()
        page.keyboard.press("Enter")
        search = page.locator("div.modal-dialog.modal-lg").get_by_role("searchbox")
        search.press_sequentially("Sample Item", delay=150)
        page.wait_for_timeout(4000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
        _dump(page, "flow_variant")
        focus = "() => document.activeElement ? document.activeElement.outerHTML.slice(0, 400) : ''"
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
        _dump(page, "flow_qty_window")
        (OUT / "flow_focus.txt").write_text("after variant enter: " + page.evaluate(focus) + "\n")
        page.keyboard.press("Control+A"); page.keyboard.type("1"); page.keyboard.press("Tab")
        page.wait_for_timeout(1500)
        with open(OUT / "flow_focus.txt", "a") as fh:
            fh.write("after qty tab: " + page.evaluate(focus) + "\n")
        page.keyboard.press("Tab")
        page.wait_for_timeout(1500)
        with open(OUT / "flow_focus.txt", "a") as fh:
            fh.write("after second tab: " + page.evaluate(focus) + "\n")
        _dump(page, "flow_variant_qty")
        page.keyboard.press("F10")
        page.wait_for_timeout(4000)
        _dump(page, "flow_bill_line")
        number = bill.document_number()
        (OUT / "flow_bill_no.txt").write_text(number)
        bill.save()
        page.wait_for_timeout(5000)
        _dump(page, "flow_bill_save_window")
        bill.confirm_save_window()
        page.wait_for_timeout(8000)
        _dump(page, "flow_bill_after_save")
        bill.screen.close_print_window_if_shown()
        page.wait_for_timeout(3000)
        _dump(page, "flow_bill_after_print")
        bill.leave_to_list()

        receipt = ReceiptPage(page)
        receipt.open_new_voucher()
        receipt.choose_mode("Cash Account")
        receipt.select_account(0, party.name)
        from datetime import date
        receipt.enter_row_date(date.today())
        receipt.enter_amount("40")
        page.wait_for_timeout(2000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        _dump(page, "flow_receipt_adjust_open")
        window = page.locator("ngb-modal-window").filter(has_text="Bill Adjustment")
        row = window.locator('[col-id="cus_invoiceNo"]').filter(has_text=number).first
        row.click()
        page.keyboard.press("Space")
        page.wait_for_timeout(2000)
        _dump(page, "flow_receipt_adjust_selected")
        page.keyboard.press("F10")
        page.wait_for_timeout(4000)
        _dump(page, "flow_receipt_adjust_saved")
        receipt.save()
        page.wait_for_timeout(5000)
        _dump(page, "flow_receipt_save")
        receipt.expect_saved()
        _dump(page, "flow_receipt_saved")

        page.get_by_role("link", name="Report").first.click()
        page.wait_for_timeout(8000)
        section = page.locator("text=Receivable").first
        section.locator("xpath=following::*[normalize-space(text())='Ledger Wise'][1]").click()
        page.wait_for_timeout(10000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        box = page.locator("#SearchBox, input[placeholder='Search here..']").first
        box.press_sequentially(party.name, delay=80)
        page.wait_for_timeout(4000)
        _dump(page, "flow_receivable_search")
        page.get_by_text(party.name, exact=True).first.dblclick()
        page.wait_for_timeout(10000)
        _dump(page, "flow_billwise")
    finally:
        _dump(page, "flow_final")


def test_flow_after_bill(page_as):
    """Continues on the party and bill saved by test_flow_with_new_party."""
    from datetime import date

    from pages.accounting.receipt_page import ReceiptPage

    party = (OUT / "flow_party.txt").read_text().strip()
    number = (OUT / "flow_bill_no.txt").read_text().strip()
    page = page_as("garments")
    DashboardPage(page).open()
    try:
        receipt = ReceiptPage(page)
        receipt.open_new_voucher()
        receipt.choose_mode("Cash Account")
        receipt.select_account(0, party)
        receipt.enter_row_date(date.today())
        receipt.enter_amount("40")
        page.wait_for_timeout(2000)
        _dump(page, "r_after_amount")
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        _dump(page, "r_adjust_open")
        window = page.locator("ngb-modal-window").filter(has_text="Bill Adjustment")
        cell = window.locator('[col-id="cus_invoiceNo"]').get_by_text(number, exact=True)
        cell.click()
        page.keyboard.press("Space")
        page.wait_for_timeout(2000)
        focus = "() => document.activeElement ? document.activeElement.outerHTML.slice(0, 300) : ''"
        (OUT / "r_focus.txt").write_text("after space: " + page.evaluate(focus) + "\n")
        _dump(page, "r_adjust_selected")
        page.keyboard.press("F10")
        page.wait_for_timeout(4000)
        _dump(page, "r_adjust_saved")
        number_cell = receipt.voucher_number()
        (OUT / "r_number.txt").write_text(number_cell)
        receipt.save()
        page.wait_for_timeout(5000)
        _dump(page, "r_save")
        receipt.expect_saved()
        _dump(page, "r_saved")

        DashboardPage(page).open()
        page.get_by_role("link", name="Report").first.click()
        page.wait_for_timeout(8000)
        section = page.get_by_text("Receivable", exact=True).first
        section.locator("xpath=following::*[normalize-space(text())='Ledger Wise'][1]").click()
        page.wait_for_timeout(10000)
        _dump(page, "rep_filter")
        page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        page.keyboard.press("F7")
        page.wait_for_timeout(5000)
        _dump(page, "rep_all")
        box = page.get_by_role("searchbox").or_(page.get_by_placeholder("Search here..")).first
        box.press_sequentially(party, delay=80)
        page.wait_for_timeout(4000)
        _dump(page, "rep_search")
        page.get_by_text(party, exact=True).first.dblclick()
        page.wait_for_timeout(10000)
        _dump(page, "rep_billwise")

        from pages.sale.documents.bill import SaleBillDocument
        DashboardPage(page).open()
        bill = SaleBillDocument(page)
        bill.screen.open_menu(bill.menu)
        bill.screen.search_list(number)
        _dump(page, "del_list")
        bill.screen.row_action(number, "Delete")
        page.wait_for_timeout(6000)
        _dump(page, "del_after_click")
    finally:
        _dump(page, "after_bill_final")


def test_report_and_delete(page_as):
    party = (OUT / "flow_party.txt").read_text().strip()
    number = (OUT / "flow_bill_no.txt").read_text().strip()
    page = page_as("garments")
    DashboardPage(page).open()
    try:
        DashboardPage(page).open()
        page.get_by_role("link", name="Report").first.click()
        page.wait_for_timeout(8000)
        section = page.get_by_text("Receivable", exact=True).first
        section.locator("xpath=following::*[normalize-space(text())='Ledger Wise'][1]").click()
        page.wait_for_timeout(10000)
        _dump(page, "rep_filter")
        page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        page.keyboard.press("F7")
        page.wait_for_timeout(5000)
        _dump(page, "rep_all")
        box = page.get_by_role("searchbox").or_(page.get_by_placeholder("Search here..")).first
        box.press_sequentially(party, delay=80)
        page.wait_for_timeout(4000)
        _dump(page, "rep_search")
        page.get_by_text(party, exact=True).first.dblclick()
        page.wait_for_timeout(10000)
        _dump(page, "rep_billwise")

        from pages.sale.documents.bill import SaleBillDocument
        DashboardPage(page).open()
        bill = SaleBillDocument(page)
        bill.screen.open_menu(bill.menu)
        bill.screen.search_list(number)
        _dump(page, "del_list")
        bill.screen.row_action(number, "Delete")
        page.wait_for_timeout(6000)
        _dump(page, "del_after_click")
    finally:
        _dump(page, "rd_final")


def test_bill_row_menu(page_as):
    from pages.sale.documents.bill import SaleBillDocument

    number = (OUT / "flow_bill_no.txt").read_text().strip()
    page = page_as("garments")
    DashboardPage(page).open()
    bill = SaleBillDocument(page)
    bill.screen.open_menu(bill.menu)
    bill.screen.search_list(number)
    page.wait_for_timeout(3000)
    row = page.get_by_role("row").filter(has=page.get_by_text(number, exact=True)).first
    (OUT / "menu_row.html").write_text(row.inner_html())
    row.locator('button[data-toggle="dropdown"]').first.click()
    page.wait_for_timeout(2000)
    _dump(page, "menu_open")
    (OUT / "menu_items.txt").write_text("\n".join(page.locator(".dropdown-menu.show").all_inner_texts()))


def test_exempt_item_line(page_as):
    from decimal import Decimal

    from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk

    party = (OUT / "flow_party.txt").read_text().strip()
    page = page_as("garments")
    DashboardPage(page).open()
    try:
        item = "QA Outstanding Exempt Item"
        desk = SaleBillDesk(page, item)
        desk._start(party, Decimal(1000))
        page.wait_for_timeout(3000)
        _dump(page, "ex_bill_line")
    finally:
        _dump(page, "ex_final")


def test_sale_return_flow(page_as):
    from pages.sale.documents.returns import MANUAL_RETURN, SaleReturn

    party = (OUT / "flow_party.txt").read_text().strip()
    page = page_as("garments")
    DashboardPage(page).open()
    try:
        ret = SaleReturn(page)
        ret.open_new()
        _dump(page, "sr_open")
        ret.choose_party_for_return(party, MANUAL_RETURN)
        _dump(page, "sr_party")
        ret.grid.cell(0, "itemLinkID").click()
        page.keyboard.press("Enter")
        ret.selection.choose_cell_value("Sample Item")
        page.wait_for_timeout(3000)
        _dump(page, "sr_after_item")
        qty = page.locator("#txt-qty-0")
        if not qty.is_visible():
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
        _dump(page, "sr_qty_window")
        qty.click(); qty.press("Control+A"); qty.press_sequentially("1")
        page.keyboard.press("F10")
        page.wait_for_timeout(3000)
        _dump(page, "sr_line")
        (OUT / "sr_number.txt").write_text(ret.document_number())
        ret.save()
        page.wait_for_timeout(5000)
        _dump(page, "sr_save1")
        for n in range(2, 5):
            page.wait_for_timeout(4000)
            _dump(page, f"sr_save{n}")
    finally:
        _dump(page, "sr_final")


def test_receipt_modify_mode(page_as):
    from pages.accounting.outstanding.credit_desks import ReceiptDesk

    page = page_as("garments")
    DashboardPage(page).open()
    focus = "() => document.activeElement ? document.activeElement.outerHTML.slice(0, 300) : ''"
    try:
        desk = ReceiptDesk(page)
        desk._open("0000020")
        _dump(page, "rm_view")
        page.keyboard.press("F3")
        page.wait_for_timeout(4000)
        _dump(page, "rm_modify")
        (OUT / "rm_focus.txt").write_text("after F3: " + page.evaluate(focus) + "\n")
        body = page.locator('[ref="eBodyContainer"]').first
        (OUT / "rm_cols.txt").write_text(" ".join(body.locator('[row-id="0"] [col-id]').evaluate_all("els => els.map(e => e.getAttribute('col-id'))")))
        cell = body.locator('[row-id="0"] [col-id="crAmount"]')
        cell.click()
        page.wait_for_timeout(1500)
        with open(OUT / "rm_focus.txt", "a") as fh:
            fh.write("after click credit: " + page.evaluate(focus) + "\n")
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
        _dump(page, "rm_after_enter")
        with open(OUT / "rm_focus.txt", "a") as fh:
            fh.write("after enter: " + page.evaluate(focus) + "\n")
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
        _dump(page, "rm_after_enter2")
    finally:
        _dump(page, "rm_final")


def test_ledger_f8_route(page_as):
    from pages.masters.master_list import LedgerList

    party = (OUT / "flow_party.txt").read_text().strip()
    page = page_as("garments")
    DashboardPage(page).open()
    try:
        ledgers = LedgerList(page)
        ledgers.open()
        ledgers.search(party)
        page.wait_for_timeout(2000)
        row = page.get_by_role("row").filter(has=page.get_by_text(party, exact=True)).first
        row.get_by_role("gridcell").first.click()
        page.wait_for_timeout(1000)
        _dump(page, "f8_list")
        page.keyboard.press("F8")
        page.wait_for_timeout(10000)
        _dump(page, "f8_after")
    finally:
        _dump(page, "f8_final")


def test_bill_modify_below_receipt(page_as, run_id):
    from decimal import Decimal

    from pages.accounting.outstanding.credit_desks import ReceiptDesk
    from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
    from pages.masters.master_records import MasterRecords
    from test_data.masters import MasterDataFactory

    page = page_as("garments")
    DashboardPage(page).open()
    try:
        party = MasterRecords(page, MasterDataFactory(run_id)).saved_customer().name
        bills = SaleBillDesk(page, "QA Outstanding Exempt Item")
        number = bills.create(party, Decimal(1500), Decimal(0))
        ReceiptDesk(page).create(party, Decimal(1200), {number: Decimal(1200)})
        bills._open_for_change(number)
        bills._reprice(Decimal(1000))
        bills._open_payment_window()
        _dump(page, "bm_payment")
        page.locator("ngb-modal-window").filter(has_text="Mode Of Payment").locator("#btn-Save").click()
        for n in (1, 3, 6, 10):
            page.wait_for_timeout(n * 1000)
            _dump(page, f"bm_after_save_{n}")
    finally:
        _dump(page, "bm_final")


def test_receipt_modify_toggles(page_as, run_id):
    from decimal import Decimal

    from pages.accounting.outstanding.credit_desks import ReceiptDesk
    from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
    from pages.masters.master_records import MasterRecords
    from test_data.masters import MasterDataFactory

    page = page_as("garments")
    DashboardPage(page).open()
    log = OUT / "tg_log.txt"
    log.write_text("")
    win = page.locator("ngb-modal-window").filter(has_text="Bill Adjustment")

    def state(tag):
        sel = win.get_by_text("Selected Bills").locator("..").inner_text() if win.is_visible() else "-"
        ed = page.locator("#txt-adjustmentAmount-0").is_visible()
        rows = win.locator('#billAdjustmentGrid [ref="eBodyContainer"] .ag-row-selected').count() if win.is_visible() else -1
        with open(log, "a") as fh:
            fh.write(f"{tag}: {' '.join(sel.split())} editor={ed} selected_rows={rows}\n")

    try:
        party = MasterRecords(page, MasterDataFactory(run_id)).saved_customer().name
        number = SaleBillDesk(page, "QA Outstanding Exempt Item").create(party, Decimal(1000), Decimal(0))
        desk = ReceiptDesk(page)
        voucher = desk.create(party, Decimal(400), {number: Decimal(400)})
        (OUT / "tg_ids.txt").write_text(f"{party} {number} {voucher}")
        desk._open_for_change(voucher)
        desk._type_party_amount(Decimal(700))
        win.wait_for(state="visible", timeout=20000)
        state("open")
        cell = win.locator('[col-id="cus_invoiceNo"]').get_by_text(number, exact=True)
        cell.click(); page.wait_for_timeout(800); state("click")
        page.keyboard.press("Space"); page.wait_for_timeout(1500); state("space1")
        cell.click(); page.wait_for_timeout(800); state("click2")
        page.keyboard.press("Space"); page.wait_for_timeout(1500); state("space2")
        _dump(page, "tg_after_space2")
        page.keyboard.press("Space"); page.wait_for_timeout(1500); state("space3 (no click)")
        page.keyboard.press("Space"); page.wait_for_timeout(1500); state("space4 (no click)")
        _dump(page, "tg_end")
        page.keyboard.press("Escape")
        page.wait_for_timeout(1500)
        _dump(page, "tg_after_escape")
    finally:
        _dump(page, "tg_final")


def test_unadjust_receipt(page_as, run_id):
    from decimal import Decimal

    from pages.accounting.outstanding.credit_desks import ReceiptDesk
    from pages.accounting.outstanding.outstanding_report import OutstandingReport
    from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
    from pages.masters.master_records import MasterRecords
    from test_data.masters import MasterDataFactory

    page = page_as("garments")
    DashboardPage(page).open()
    try:
        party = MasterRecords(page, MasterDataFactory(run_id)).saved_customer().name
        number = SaleBillDesk(page, "QA Outstanding Exempt Item").create(party, Decimal(1000), Decimal(0))
        desk = ReceiptDesk(page)
        voucher = desk.create(party, Decimal(1000), {number: Decimal(1000)})
        (OUT / "ua_ids.txt").write_text(f"{party} {number} {voucher}")
        desk._open_for_change(voucher)
        desk._open_adjustment_from_amount()
        _dump(page, "ua_window")
        desk._adjustment.unselect_all()
        _dump(page, "ua_unselected")
        page.keyboard.press("F10")
        page.wait_for_timeout(2500)
        _dump(page, "ua_f10")
        from pages.accounting.confirmation import Confirmation
        Confirmation(page).answer_yes_if_asked()
        page.wait_for_timeout(2500)
        _dump(page, "ua_yes")
        page.keyboard.press("F10")
        page.wait_for_timeout(2500)
        _dump(page, "ua_f10_2")
        desk._save()
        _dump(page, "ua_saved")
        print(OutstandingReport(page).read(party))
        _dump(page, "ua_report")
        desk._open_for_change(voucher)
        desk._open_adjustment_from_amount()
        _dump(page, "ua_reopened")
    finally:
        _dump(page, "ua_final")


def test_receipt_list_columns(page_as):
    from pages.accounting.accounting_menu import AccountingMenu
    from pages.accounting.list_screen import ListScreen

    party = (OUT / "flow_party.txt").read_text().strip()
    page = page_as("garments")
    DashboardPage(page).open()
    AccountingMenu(page).open_screen("Receipt")
    vouchers = ListScreen(page)
    vouchers.filter_to_this_week()
    vouchers.search(party)
    page.wait_for_timeout(4000)
    _dump(page, "rl_list")
    import re
    h = page.content()
    (OUT / "rl_cols.txt").write_text(" ".join(re.findall(r'class="ag-header-cell[^"]*"[^>]*col-id="([^"]+)"', h)))
