"""Fixtures for J14: a garments session (the account the purchase suite uses), an item with opening stock,
a saved purchase return and a saved debit note voucher. Returns and vouchers are deleted afterwards; the
item cannot be (it has opening stock, see specs/purchase-return-debit-note.md).
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.debit_note_page import DebitNotePage
from pages.company_switch_page import GARMENTS_COMPANY
from pages.returns.debit_note_entry import save_debit_note
from pages.returns.debit_note_list import DebitNoteList
from pages.returns.manual_return import ManualPurchaseReturn, ManualReturn
from pages.returns.return_list import PurchaseReturnList
from pages.stock.item_stock_balance import ItemStockBalance
from pages.stock.opening_stock import create_item_with_opening
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec
from test_data.purchase_returns import (
    OPENING_QUANTITY,
    debit_note_voucher,
    manual_return_of,
    returnable_item,
)

RETURNS_ACCOUNT: Account = "garments"


@pytest.fixture
def returns_page(company_page: Callable[[Account, str], Page]) -> Page:
    return company_page(RETURNS_ACCOUNT, GARMENTS_COMPANY)


@pytest.fixture
def item_in_stock(returns_page: Page, data: DataFactory, run_id: str) -> ItemMasterSpec:
    item = returnable_item(data, run_id)
    create_item_with_opening(returns_page, item, OPENING_QUANTITY)
    # A new item shows stock 0 in "Select Item" until its balance is refreshed, and is then not taken
    # (specs/inventory.md D6); the refresh makes the opening stock usable.
    ItemStockBalance(returns_page).main_store_stock(item.product)
    return item


@pytest.fixture
def refused_proposals() -> list[str]:
    """Numbers the app proposed for a return of this test and then refused as already used."""
    return []


@pytest.fixture
def own_number(run_id: str) -> str:
    return f"DN{run_id}"


@pytest.fixture
def numbering(own_number: str, refused_proposals: list[str]) -> tuple[str, list[str]]:
    """This test's own Dr. Note number and the list that collects the numbers the app proposed and refused."""
    return own_number, refused_proposals


@pytest.fixture
def saved_return(
    returns_page: Page, item_in_stock: ItemMasterSpec, numbering: tuple[str, list[str]]
) -> Iterator[tuple[ManualReturn, str]]:
    """A manual return of part of the item's stock to the cash party, and its Dr. Note number."""
    own_number, refused_proposals = numbering
    goods = manual_return_of(item_in_stock)
    returns = ManualPurchaseReturn(returns_page)
    number = returns.create_manual(goods, own_number)
    refused_proposals.extend([returns.refused_proposal] if returns.refused_proposal else [])
    yield goods, number
    listing = PurchaseReturnList(returns_page)
    listing.find(number)
    if listing.is_listed(number):
        returns.delete_from_list(number)


@pytest.fixture
def saved_debit_note(returns_page: Page, run_id: str) -> Iterator[str]:
    """A debit note voucher of this test, dated today; its number."""
    number = save_debit_note(DebitNotePage(returns_page), debit_note_voucher(run_id))
    yield number
    listing = DebitNoteList(returns_page)
    listing.find(number)
    if listing.is_listed(number):
        listing.delete(number)
