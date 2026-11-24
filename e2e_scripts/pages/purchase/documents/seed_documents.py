"""Creates the earlier documents a test builds on, so that no test depends on another one (rule 4).

The original chains order -> challan -> bill -> return through files written by the previous test. Here each
test that needs an earlier document makes its own, with the same data the original used for it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Page

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.challan_page import PurchaseChallanPage
from pages.purchase.documents.dates import timestamp_label, todays_serial
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.line_items import PurchaseLineItem, standard_line
from pages.purchase.documents.order_page import PurchaseOrderPage

SEED_PARTY = "Cash Account"
SEED_BILL_DISCOUNT = Decimal(10)


@dataclass(frozen=True)
class SeededBill:
    number: str
    batch: str
    line: PurchaseLineItem


def seed_draft(batch: str = "") -> PurchaseDraft:
    """Cash Account, dated today, the standard line (100 + 50 free at 100), 10 bill discount."""
    line = standard_line().with_batch(batch)
    return PurchaseDraft(
        party=SEED_PARTY,
        entry_date=todays_serial(),
        lines=(line,),
        bill_discount=SEED_BILL_DISCOUNT,
        invoice_date=todays_serial(),
    )


def seed_order(page: Page) -> str:
    return PurchaseOrderPage(page).create(seed_draft())


def seed_challan(page: Page) -> str:
    return PurchaseChallanPage(page).create(seed_draft(timestamp_label()))


def seed_bill(
    page: Page, bill_page: Callable[[Page], PurchaseBillEntryPage] = PurchaseBillEntryPage
) -> SeededBill:
    """A saved bill; it also puts the standard line's stock and batch into the system. `bill_page` is the
    screen class to save it through, for a tenant whose bill screen behaves differently."""
    batch = timestamp_label()
    draft = seed_draft(batch)
    number = bill_page(page).create(draft)
    return SeededBill(number, batch, draft.lines[0])


def seed_stock_for(page: Page, draft: PurchaseDraft) -> PurchaseDraft:
    """A return needs an existing batch with stock. Makes one by a bill and points the draft's lines at it."""
    if not any(line.product for line in draft.lines):
        return draft
    return draft.with_batch(seed_bill(page).batch)
