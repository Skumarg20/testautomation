"""Ajay rows 58, 123, 124, 125 and Sale checklist row 40: billing from a store.

The garments company already has "Main Store" and "Scrap Store". A test item gets opening stock 10 in the Main
Store, then 4 are transferred to the Scrap Store, so the book stock is Main 6 and Scrap 4 (arithmetic below).
"Ask Store?" is held at Yes and the Store box is filled after the party. The item has stock, so it stays
(permanent). Stock per store is read as "As Per Book" on an unsaved Physical Stock entry.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.components.bill_totals import BillTotals
from pages.masters.round2_c2.owned_items import OwnedItems
from pages.masters.round2_c2.owned_parties import OwnedParties
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.manual.bill_messages import BillMessages
from pages.sale.manual.option_settings import NEGATIVE_ALLOWED, HeldOptions, SaleBillSettings
from pages.sale.round2_c2.store_billing import ASK_STORE, STOCK_REFUSED, StoreBillDesk, book_stock
from pages.stock.stock_transfer_page import StockTransferPage, StoreTransfer
from test_data.models import ItemMasterSpec
from test_data.stock_movement import MAIN_STORE, SCRAP_STORE

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
    pytest.mark.permanent("an item with opening stock (QA-<run>-Item1) stays in the garments company"),
]

OPENING = Decimal(10)
MOVED = Decimal(4)
SOLD = Decimal(1)
SALE_AMOUNT = Decimal(150)


@dataclass(frozen=True)
class Stage:
    page: Page
    stock_page: Page
    item: ItemMasterSpec
    party: str
    desk: StoreBillDesk
    held: HeldOptions


@pytest.fixture
def stock_item(stock_page: Page, items: OwnedItems) -> tuple[Page, ItemMasterSpec]:
    """An item with 10 in the Main Store, 4 of them moved to the Scrap Store."""
    item = items.saved_with_opening(items.spec(), OPENING)
    StockTransferPage(stock_page).transfer(StoreTransfer(item.product, MOVED, (MAIN_STORE, SCRAP_STORE)))
    return stock_page, item


@pytest.fixture
def store_party(guarded_page: Page, parties: OwnedParties) -> str:
    party = parties.saved_with_email().name
    PartyAvailability(guarded_page).wait_until_selectable(party)
    return party


@pytest.fixture
def stage(guarded_page: Page, stock_item: tuple[Page, ItemMasterSpec], store_party: str) -> Iterator[Stage]:
    stock_page, item = stock_item
    party = store_party
    bill = SaleBillDocument(guarded_page)
    held = HeldOptions(
        SaleBillSettings(guarded_page), bill.open_new, BillTotals(guarded_page).leave_without_saving
    )
    held.hold(ASK_STORE, "Yes")
    yield Stage(guarded_page, stock_page, item, party, StoreBillDesk(guarded_page, item.product), held)
    held.close()


def test_sale_from_a_store_takes_stock_from_that_store_only(stage: Stage) -> None:
    """Rows 58, 125 and checklist 40: one piece sold from the Scrap Store: Scrap 4 - 1 = 3, Main stays 6."""
    number = stage.desk.create_in_store(stage.party, SCRAP_STORE, SALE_AMOUNT)

    try:
        assert book_stock(stage.stock_page, SCRAP_STORE, stage.item.product) == MOVED - SOLD
        assert book_stock(stage.stock_page, MAIN_STORE, stage.item.product) == OPENING - MOVED
    finally:
        stage.desk.delete(number)


def test_quantity_above_the_stores_stock_is_refused(stage: Stage) -> None:
    """Row 123: with negative stock not allowed, 5 pieces cannot be sold from the Scrap Store, which holds 4
    (the other 6 are in the Main Store); the bill warns about the salable stock."""
    stage.held.hold(NEGATIVE_ALLOWED, "No")
    stage.desk.open_in_store(stage.party, SCRAP_STORE)

    stage.desk.pick_item_only(stage.item.product, MOVED + 1)

    BillMessages(stage.page).expect_warning_like(STOCK_REFUSED)
    BillTotals(stage.page).leave_without_saving()


def test_store_changed_after_the_item_deducts_from_the_new_store(stage: Stage) -> None:
    """Row 124: the item is added under the Main Store, the store is changed to Scrap, then the bill is saved:
    Scrap 4 - 1 = 3 and Main stays 6."""
    stage.desk.open_in_store(stage.party, MAIN_STORE)
    stage.desk.add_line(SALE_AMOUNT)
    stage.desk.change_store(SCRAP_STORE)

    number = stage.desk.save_open_bill(stage.party)

    try:
        assert book_stock(stage.stock_page, SCRAP_STORE, stage.item.product) == MOVED - SOLD
        assert book_stock(stage.stock_page, MAIN_STORE, stage.item.product) == OPENING - MOVED
    finally:
        stage.desk.delete(number)
