"""J40 Material Issue and Material Received beyond the happy path: line rate and amount (MF-15), the party
window (MF-16), negative stock (MF-17), receives that do not match the BOM or the issue (MF-21, MF-22),
changing and deleting saved vouchers (MF-26) and dates outside the books year (MF-36).

Figures are the pack's worked example (RM-A 100, RM-B 50, BOM FG 1 = RM-A 2 + RM-B 1, issue for 10 sets).
"""

import re
from collections.abc import Callable
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.company_switch_page import CompanySwitchPage
from pages.manufacturing.menu import ManufacturingScreen
from pages.manufacturing.stock_vouchers import (
    MaterialIssue,
    MaterialReceive,
    RawMaterialsConsumedWindow,
    SavedVoucher,
    StockVoucherForm,
)
from pages.manufacturing.voucher_checks import PartyWindow, VoucherDate, VoucherLines, open_for_change
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.entry_grid import EntryGrid
from pages.stock.item_stock_balance import ItemStockBalance
from pages.stock.messages import StockMessages
from test_data.manufacturing import (
    PRODUCTION_DEPARTMENT,
    RM_A_BEYOND_STOCK,
    RM_A_OPENING,
    RM_B_OPENING,
    SETS_BELOW_BOM_QUANTITY,
    SETS_ISSUED,
    SETS_ISSUED_AFTER_CHANGE,
    SETS_NOT_A_MULTIPLE,
    BomSpec,
    OutsideBooksYear,
    StockItem,
)

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ReceiveWindow = Callable[[BomSpec, Decimal], RawMaterialsConsumedWindow]
NOT_A_MANUFACTURER = "Cash"
GOING_NEGATIVE = re.compile(r"Stock going in negative!")
ISSUE_UPDATED = re.compile(r"Sale Bill updated successfully!")
RECEIVE_UPDATED = re.compile(r"Updated successfully!")


def test_issue_line_rate_is_the_item_master_rate(saved_bom: BomSpec, bom_page: Page) -> None:
    """MF-15: Rate comes from the item master (KB-doc BOM_v1.0 "Material Issue"; Rate A of our items)."""
    raw_a = saved_bom.raw_materials[0]
    issue = MaterialIssue(bom_page)
    issue.open_new()
    issue.add_line(0, raw_a.item.product, raw_a.for_sets(SETS_ISSUED))
    assert VoucherLines(bom_page).rate(0) == raw_a.item.sale_rate


def test_issue_line_amount_is_quantity_times_rate(saved_bom: BomSpec, bom_page: Page) -> None:
    """MF-15: Amount = Qty x Rate (the pack's 20 x 150 = 3000.00 with our item's rate)."""
    raw_a = saved_bom.raw_materials[0]
    issue = MaterialIssue(bom_page)
    issue.open_new()
    issue.add_line(0, raw_a.item.product, raw_a.for_sets(SETS_ISSUED))
    lines = VoucherLines(bom_page)
    assert lines.amount(0) == raw_a.for_sets(SETS_ISSUED) * lines.rate(0)


def test_issue_party_window_offers_production_department(bom_page: Page) -> None:
    """MF-16: the predefined manufacturer ledger is offered (KB `#25e8dd21`)."""
    MaterialIssue(bom_page).start_new()
    window = PartyWindow(bom_page)
    window.search(PRODUCTION_DEPARTMENT)
    window.expect_offered(PRODUCTION_DEPARTMENT)


def test_issue_party_window_leaves_out_ledgers_of_other_groups(bom_page: Page) -> None:
    """MF-16: only Sundry Creditor (Manufacturer) ledgers, so "Cash" is not offered (factory.ts:29)."""
    MaterialIssue(bom_page).start_new()
    window = PartyWindow(bom_page)
    window.search(NOT_A_MANUFACTURER)
    window.expect_not_offered(NOT_A_MANUFACTURER)


def test_issue_beyond_stock_is_warned_when_negative_stock_is_not_allowed(
    raw_materials: tuple[StockItem, StockItem], negative_stock_refused: Page
) -> None:
    """MF-17: Stock Negative allowed = No: RM-A 120 against 100 gives "Stock going in negative!"
    (global.ts:19322; whether BOM issue follows the sale rule is UNVERIFIED, so this is the question)."""
    issue = MaterialIssue(negative_stock_refused)
    issue.open_new()
    issue.add_line(0, raw_materials[0].product, RM_A_BEYOND_STOCK)
    StockMessages(negative_stock_refused).expect_shown(GOING_NEGATIVE)


def test_issue_beyond_stock_takes_the_raw_material_negative_when_allowed(
    issue_beyond_stock: SavedVoucher, raw_materials: tuple[StockItem, StockItem], bom_page: Page
) -> None:
    """MF-17: Stock Negative allowed = Yes: saved, and RM-A shows 100 - 120 = -20."""
    assert (
        ItemStockBalance(bom_page).main_store_stock(raw_materials[0].product)
        == RM_A_OPENING - RM_A_BEYOND_STOCK
    )


def test_receive_below_the_bom_quantity_is_refused(
    saved_bom_of_two: BomSpec, receive_window: ReceiveWindow, bom_page: Page
) -> None:
    """MF-21: BOM Qty 2, receive 1: "Minimum Quantity Should be :2" (billofmaterialdetails.ts:211-213)."""
    receive_window(saved_bom_of_two, SETS_BELOW_BOM_QUANTITY)
    minimum = re.compile(rf"Minimum Quantity Should be :{saved_bom_of_two.quantity}")
    StockMessages(bom_page).expect_shown(minimum)


def test_receive_of_a_non_multiple_scales_the_raw_materials(
    saved_bom_of_two: BomSpec, receive_window: ReceiveWindow
) -> None:
    """MF-21: receive 3 of a BOM for 2: factor 1.5, so RM-A 4 x 1.5 = 6 and RM-B 2 x 1.5 = 3."""
    window = receive_window(saved_bom_of_two, SETS_NOT_A_MULTIPLE)
    for component in saved_bom_of_two.raw_materials:
        window.expect_quantity(
            component.item.product, saved_bom_of_two.needed_for(component, SETS_NOT_A_MULTIPLE)
        )


def test_receive_without_an_issue_is_refused(saved_bom: BomSpec, receive_window: ReceiveWindow) -> None:
    """MF-22: nothing pending with Production Department: "<RM-A> Quantity Not Available"."""
    raw_a = saved_bom.raw_materials[0].item.product
    window = receive_window(saved_bom, SETS_ISSUED)
    window.expect_refused(re.compile(rf"{re.escape(raw_a)} Quantity Not Available"))


def test_deleted_issue_puts_the_raw_materials_back(
    own_issue: SavedVoucher, saved_bom: BomSpec, stock: ItemStockBalance
) -> None:
    """MF-26: deleting the issue of 10 sets: RM-A back to 100, RM-B back to 50."""
    own_issue.delete()
    raw_a, raw_b = saved_bom.raw_materials
    assert stock.main_store_stock(raw_a.item.product) == RM_A_OPENING
    assert stock.main_store_stock(raw_b.item.product) == RM_B_OPENING


def test_changed_issue_takes_out_the_new_quantity(
    own_issue: SavedVoucher, saved_bom: BomSpec, stock: ItemStockBalance
) -> None:
    """MF-26: the issue changed from 10 to 15 sets: RM-A 100 - 30 = 70."""
    raw_a = saved_bom.raw_materials[0]
    open_for_change(stock.page, ManufacturingScreen.MATERIAL_ISSUE, own_issue.number)
    EntryGrid(stock.page).enter_quantity(0, raw_a.for_sets(SETS_ISSUED_AFTER_CHANGE))
    _save_change(MaterialIssue(stock.page))
    assert stock.main_store_stock(raw_a.item.product) == RM_A_OPENING - raw_a.for_sets(
        SETS_ISSUED_AFTER_CHANGE
    )


def test_deleted_receive_takes_the_finished_items_off_again(
    own_receive: SavedVoucher, saved_bom: BomSpec, stock: ItemStockBalance
) -> None:
    """MF-26: deleting the receive of 10: FG back to 0."""
    own_receive.delete()
    assert stock.main_store_stock(saved_bom.finished.product) == 0


def test_receive_batch_change_is_saved(own_receive: SavedVoucher, bom_page: Page) -> None:
    """MF-26 / MB-038971: changing the batch of a saved receive saves (" Updated successfully!"), no
    "Bad Request"."""
    open_for_change(bom_page, ManufacturingScreen.MATERIAL_RECEIVE, own_receive.number)
    if not VoucherLines(bom_page).has_batch_column():
        pytest.skip("MF-26: needs batch-wise items on GANE29; the receive grid shows no Batch column")
    EntryGrid(bom_page).type_batch(0, timestamp_label())
    receive = MaterialReceive(bom_page)
    receive.save()
    StockMessages(bom_page).expect_shown(RECEIVE_UPDATED)


def test_issue_dated_before_the_books_year_is_refused(bom_page: Page) -> None:
    """MF-36: "Invalid entry date ! Date should be between financial year." (processout...ts:1832)."""
    outside = OutsideBooksYear.around(CompanySwitchPage(bom_page).current_year())
    MaterialIssue(bom_page).open_new()
    date = VoucherDate(bom_page)
    date.enter(outside.day_before)
    date.expect_outside_books_year_refused()


def test_receive_dated_after_the_books_year_is_refused(bom_page: Page) -> None:
    """MF-36: the same check on the purchase-type screen (transactionin.component.ts:2200)."""
    outside = OutsideBooksYear.around(CompanySwitchPage(bom_page).current_year())
    MaterialReceive(bom_page).open_new()
    date = VoucherDate(bom_page)
    date.enter(outside.day_after)
    date.expect_outside_books_year_refused()


def _save_change(voucher: StockVoucherForm) -> None:
    voucher.save()
    StockMessages(voucher.page).expect_shown(ISSUE_UPDATED)
