"""J14 purchase return (Purchase > Return), the cases the older purchase-itc tests do not cover.

Plan: specs/purchase-return-debit-note.md (PRD-01, PRD-02, LNK-01, LNK-03, RT-E).
"""

import pytest
from playwright.sync_api import Page

from pages.returns.debit_note_list import DebitNoteList
from pages.returns.manual_return import ManualPurchaseReturn, ManualReturn
from pages.returns.return_list import PurchaseReturnList
from pages.stock.item_stock_balance import ItemStockBalance
from test_data.models import ItemMasterSpec
from test_data.purchase_returns import CASH_PARTY, OPENING_QUANTITY

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("purchase-return-debit-note"),
    pytest.mark.xdist_group("purchase-stock"),
]

SavedReturn = tuple[ManualReturn, str]


def test_saved_return_is_listed_with_its_party_and_the_sum_of_its_lines(
    returns_page: Page, saved_return: SavedReturn
) -> None:
    goods, number = saved_return
    listing = PurchaseReturnList(returns_page)
    listing.find(number)

    listing.expect_listed(number)
    assert listing.party(number) == CASH_PARTY
    assert listing.amount(number) == goods.value


def test_returning_part_of_the_stock_lowers_it_by_the_returned_quantity(
    returns_page: Page, item_in_stock: ItemMasterSpec, saved_return: SavedReturn
) -> None:
    goods, _ = saved_return

    stock = ItemStockBalance(returns_page).main_store_stock(item_in_stock.product)

    assert stock == OPENING_QUANTITY - goods.quantity


def test_deleting_a_return_gives_the_stock_back(
    returns_page: Page, item_in_stock: ItemMasterSpec, saved_return: SavedReturn
) -> None:
    _, number = saved_return

    ManualPurchaseReturn(returns_page).delete_from_list(number)

    assert ItemStockBalance(returns_page).main_store_stock(item_in_stock.product) == OPENING_QUANTITY


def test_purchase_return_is_not_listed_among_debit_note_vouchers(
    returns_page: Page, saved_return: SavedReturn
) -> None:
    _, number = saved_return
    vouchers = DebitNoteList(returns_page)
    vouchers.find(number)

    vouchers.expect_not_listed(number)


def test_next_return_proposes_a_dr_note_number_not_yet_used(
    returns_page: Page, saved_return: SavedReturn, refused_proposals: list[str]
) -> None:
    _, number = saved_return

    proposed = ManualPurchaseReturn(returns_page).proposed_number(CASH_PARTY)

    assert proposed != number, f"a new return proposes {proposed}, the number of the saved return"
    assert proposed not in refused_proposals, (
        f"a new return proposes {proposed}, a number the app refused as used"
    )
