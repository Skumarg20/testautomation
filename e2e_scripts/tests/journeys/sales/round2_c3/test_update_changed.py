"""Sale checklist rows 75 and 76: Update Changed Rate / Update Changed Discount.

Rule, `processout.transaction.component.ts:12515-12559` and `updateRate&Discount.component.html`: when a
typed rate differs from the picked one, "Update Changed Rate" 1 No stores nothing; 2 Price List writes the
item master at once (`updateItemMasterRate`, :12638-12700, toast "Rate Record updated successfully.");
3 Ask opens the window with Don't Store, Special Rate and Price List; 4 Ask w/o Price List opens it without
the Price List button. The discount setting (lookup 1089) works the same with Product Special and Agency
List; a stored discount answers with the toast "discount Record updated successfully.". Tried on an item
the test owns, so the master it changes is deleted afterwards. Which master column Price List writes
(`rateupdate`) is not in the source read: the master is read in the Default Billing Rate column, A-Rate
(Q-C3-6).
"""

import re
from decimal import Decimal

import pytest

from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within
from pages.purchase.checklist.item_master_rates import ItemMasterRates
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.sale_fields import (
    A_RATE,
    DEFAULT_BILLING_RATE,
    ITEM_WISE,
    RATES_FROM,
    UPDATE_CHANGED_DISCOUNT,
    UPDATE_CHANGED_RATE,
)
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

MASTER_RATE = Decimal(150)
NEW_RATE = Decimal(140)
WINDOW_WAIT_MS = 5_000
RATE_STORED = re.compile("Rate Record updated successfully", re.IGNORECASE)
DISCOUNT_STORED = re.compile("discount Record updated successfully", re.IGNORECASE)
ONE_BATCH = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),), master_rate_a=MASTER_RATE)


def change_rate(desk: SaleDesk, mode: str) -> str:
    """Holds the setting, sells one piece and types NEW_RATE; returns the item code."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(RATES_FROM, ITEM_WISE)
    desk.options.hold(DEFAULT_BILLING_RATE, A_RATE)
    desk.options.hold(UPDATE_CHANGED_RATE, mode)
    desk.sell(StockLine(item, item.batch_names[0], Decimal(1)))
    desk.bill.type_rate(0, NEW_RATE)
    return item.code


def master_rate(desk: SaleDesk, code: str) -> Decimal:
    desk.bill.bill.leave_without_saving()
    return ItemMasterRates(desk.bill.bill.page).sale_rate_a_of(code)


def test_price_list_writes_the_changed_rate_to_the_item_master(desk: SaleDesk) -> None:
    """Row 75 (Price List): the master rate A becomes 140 and the success toast shows."""
    code = change_rate(desk, "Price List")

    Toasts(desk.bill.bill.page).expect_success_saying(RATE_STORED)
    assert master_rate(desk, code) == NEW_RATE


def test_no_update_leaves_the_item_master_alone(desk: SaleDesk) -> None:
    """Row 75 (No): no window, no toast, master rate A still 150."""
    code = change_rate(desk, "No")

    page = desk.bill.bill.page
    assert not appears_within(page.locator("#dontStore"), WINDOW_WAIT_MS)
    assert master_rate(desk, code) == MASTER_RATE


@pytest.mark.parametrize(("mode", "price_list_offered"), [("Ask", True), ("Ask w/o Price List", False)])
def test_ask_offers_the_choices_and_dont_store_keeps_the_master(
    desk: SaleDesk, mode: str, price_list_offered: bool
) -> None:
    """Row 75 (Ask, Ask w/o Price List): the window offers Special Rate always and Price List only for Ask;
    Don't Store leaves the master at 150."""
    code = change_rate(desk, mode)
    page = desk.bill.bill.page

    assert appears_within(page.locator("#dontStore"), WINDOW_WAIT_MS)
    assert (page.locator("#priceList").count() == 1) == price_list_offered
    page.locator("#dontStore").click()

    assert master_rate(desk, code) == MASTER_RATE


@pytest.mark.parametrize(
    ("mode", "stored"), [("Product Special", True), ("No", False)], ids=["product-special", "no"]
)
def test_changed_discount_is_stored_only_when_the_setting_says(
    desk: SaleDesk, mode: str, stored: bool
) -> None:
    """Row 76: a discount of 7 typed on the row is stored for the customer and item with Product Special
    (success toast) and not stored with No."""
    item = desk.make_stock(ONE_BATCH)
    desk.options.hold(UPDATE_CHANGED_DISCOUNT, mode)
    desk.sell(StockLine(item, item.batch_names[0], Decimal(1)))

    desk.bill.type_discount(0, Decimal(7))

    if stored:
        Toasts(desk.bill.bill.page).expect_success_saying(DISCOUNT_STORED)
    else:
        assert not appears_within(desk.bill.bill.page.locator("#dontStore"), WINDOW_WAIT_MS)
