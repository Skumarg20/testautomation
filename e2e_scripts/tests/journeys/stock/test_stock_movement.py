"""J13 inventory stock movement: opening stock, physical stock (count and process), store transfer.

Plan: specs/inventory.md (IN-01, IN-02, IN-15, IN-16, IN-19, IN-20, IN-28).
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.stock.item_stock_balance import ItemStockBalance
from pages.stock.physical_stock_page import EntryStatus, PhysicalStockPage
from pages.stock.stock_transfer_page import StockTransferPage, StoreTransfer
from test_data.models import ItemMasterSpec
from test_data.stock_movement import MAIN_STORE, OPENING_QUANTITY, SCRAP_STORE

# Physical stock entries and store transfers are numbered tenant-wide; one worker keeps the numbers apart.
pytestmark = [pytest.mark.p1, pytest.mark.journey("inventory"), pytest.mark.xdist_group("chemist-stock")]

COUNT_ABOVE_BOOK = Decimal(15)
COUNT_BELOW_BOOK = Decimal(4)
TRANSFERRED = Decimal(4)


def test_opening_stock_entered_with_a_new_item_becomes_its_stock(
    stock_page: Page, item_with_opening_stock: ItemMasterSpec
) -> None:
    stock = ItemStockBalance(stock_page).main_store_stock(item_with_opening_stock.product)

    assert stock == OPENING_QUANTITY


def test_physical_count_shows_book_stock_and_the_difference(
    stock_page: Page, item_with_opening_stock: ItemMasterSpec
) -> None:
    count = PhysicalStockPage(stock_page)
    count.start_count(MAIN_STORE, item_with_opening_stock.product)

    assert count.book_quantity() == OPENING_QUANTITY
    count.enter_counted(COUNT_ABOVE_BOOK)
    assert count.difference() == COUNT_ABOVE_BOOK - OPENING_QUANTITY
    count.abandon()


def test_saved_physical_count_is_pending_and_leaves_stock_unchanged(
    stock_page: Page, item_with_opening_stock: ItemMasterSpec
) -> None:
    voucher = _save_count(stock_page, item_with_opening_stock, COUNT_ABOVE_BOOK)

    count = PhysicalStockPage(stock_page)
    count.open_list()
    assert count.status(voucher) == EntryStatus.PENDING.value
    assert ItemStockBalance(stock_page).main_store_stock(item_with_opening_stock.product) == OPENING_QUANTITY


@pytest.mark.parametrize(
    "counted", [COUNT_ABOVE_BOOK, COUNT_BELOW_BOOK], ids=["count-above-book", "write-off"]
)
def test_processed_physical_count_sets_stock_to_the_counted_quantity(
    stock_page: Page, item_with_opening_stock: ItemMasterSpec, counted: Decimal
) -> None:
    voucher = _save_count(stock_page, item_with_opening_stock, counted)

    count = PhysicalStockPage(stock_page)
    count.open_list()
    count.process(voucher)

    assert count.status(voucher) == EntryStatus.PROCESSED.value
    assert ItemStockBalance(stock_page).main_store_stock(item_with_opening_stock.product) == counted


def test_store_transfer_moves_stock_from_one_store_to_the_other(
    stock_page: Page, item_with_opening_stock: ItemMasterSpec
) -> None:
    product = item_with_opening_stock.product
    # Until its balance is refreshed, a new item shows stock 0 in "Select Item" and the transfer does not
    # take it (specs/inventory.md D6), so the balance is refreshed first.
    ItemStockBalance(stock_page).main_store_stock(product)
    StockTransferPage(stock_page).transfer(StoreTransfer(product, TRANSFERRED, (MAIN_STORE, SCRAP_STORE)))

    main_store = ItemStockBalance(stock_page).main_store_stock(product)
    scrap_store = _book_stock(stock_page, SCRAP_STORE, product)

    assert main_store == OPENING_QUANTITY - TRANSFERRED
    assert scrap_store == TRANSFERRED
    assert main_store + scrap_store == OPENING_QUANTITY


def _save_count(page: Page, item: ItemMasterSpec, counted: Decimal) -> str:
    count = PhysicalStockPage(page)
    count.start_count(MAIN_STORE, item.product)
    count.enter_counted(counted)
    return count.save(f"{item.product} count")


def _book_stock(page: Page, store: str, product: str) -> Decimal:
    """A store's stock of a product, as the physical stock entry shows it "As Per Book" (nothing is saved)."""
    count = PhysicalStockPage(page)
    count.start_count(store, product)
    book = count.book_quantity()
    count.abandon()
    return book
