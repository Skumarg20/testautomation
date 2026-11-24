"""An item of the test's own (QA-<run_id>-Item) with stock from its own purchase bill, removed afterwards.

Steps (all existing flows): Create Item (CreateItemPage, optional Scheme Type `#Validfrom`), decline the
opening-stock question, read the item code from the item list, buy `STOCK` pieces in a new batch on a purchase
bill (DealPurchaseBill, optionally with a batch deal). Teardown deletes the purchase bill first
(stock goes back,
Document list delete) and then the item, which then has no transaction; a bill the test saved must
be deleted by
the test before this ends.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Page

from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.purchase.documents.dates import timestamp_label, todays_serial
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.line_items import STANDARD_EXPIRY, PurchaseLineItem
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.seed_documents import SEED_PARTY
from pages.purchase.round2_c1.deal_purchase import DealPurchaseBill
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

STOCK = 100
PURCHASE_RATE = 100
CODE_COLUMN = "itemcode"


@dataclass(frozen=True)
class ItemSetup:
    """What makes the item special: the batch deal (buy, free) and the item's Scheme Type text."""

    deal: tuple[int, int] = (0, 0)
    scheme_type: str = ""


@dataclass(frozen=True)
class OwnItem:
    spec: ItemMasterSpec
    code: str
    batch: str

    @property
    def name(self) -> str:
        return self.spec.product


def _create(page: Page, spec: ItemMasterSpec, scheme_type: str) -> str:
    form = CreateItemPage(page)
    form.open()
    form.fill(spec)
    if scheme_type:
        page.locator("#Validfrom").select_option(label=scheme_type)
    form.save()
    form.expect_saved()
    form.expect_opening_stock_offered()
    form.decline_opening_stock()
    items = ItemListPage(page)
    items.open()
    items.expect_listed(spec.product)
    return items.cell_text(spec.product, CODE_COLUMN)


def _buy(page: Page, code: str, deal: tuple[int, int]) -> tuple[str, str]:
    batch = timestamp_label()
    line = PurchaseLineItem(
        code, Decimal(STOCK), rate=Decimal(PURCHASE_RATE), expiry_serial=STANDARD_EXPIRY, batch=batch
    )
    draft = PurchaseDraft(
        party=SEED_PARTY, entry_date=todays_serial(), lines=(line,), invoice_date=todays_serial()
    )
    return DealPurchaseBill(page, deal).create(draft), batch


@contextmanager
def own_stocked_item(page: Page, run_id: str, setup: ItemSetup = ItemSetup()) -> Iterator[OwnItem]:  # noqa: B008
    spec = DataFactory(run_id).item_master()
    code = _create(page, spec, setup.scheme_type)
    number = ""
    try:
        number, batch = _buy(page, code, setup.deal)
        yield OwnItem(spec, code, batch)
    finally:
        _remove(page, spec.product, number)


def _remove(page: Page, product: str, purchase_number: str) -> None:
    if purchase_number:
        bill = DealPurchaseBill(page, (0, 0))
        bill.menu.open_purchase(PurchaseScreen.BILL)
        bill.documents.delete(purchase_number)
    ItemListPage(page).open()
    ItemListPage(page).delete(product)
