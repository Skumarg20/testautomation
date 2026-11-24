"""Purchase bills: direct, from an order or from a challan; delete or turn back into a challan."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.drafts import PurchaseDraft, is_yes, needs
from pages.purchase.documents.item_stock import ItemStock
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.seed_documents import seed_challan, seed_draft, seed_order
from pages.purchase.documents.support import negative, open_dashboard, positive
from test_data.document_cases import DocumentCase, case_id, cases_for

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

CASES = cases_for("purchase", "bill")


def _with_earlier_documents(page: Page, case: DocumentCase, draft: PurchaseDraft) -> PurchaseDraft:
    if needs(case, "order"):
        draft = draft.from_order(seed_order(page))
    if needs(case, "challan"):
        draft = draft.from_challan(seed_challan(page))
    return draft


def _stocked_lines(case: DocumentCase, draft: PurchaseDraft) -> tuple[PurchaseLineItem, ...]:
    """A bill made from a challan carries the challan's lines, and the challan is what takes the stock in."""
    return seed_draft().lines if needs(case, "challan") else draft.lines


@pytest.mark.parametrize("case", positive(CASES), ids=case_id)
def test_bill_is_saved_then_followed_up(page_as: Callable[[Account], Page], case: DocumentCase) -> None:
    page = open_dashboard(page_as)
    bills = PurchaseBillEntryPage(page)
    stock = ItemStock(page)
    draft = PurchaseDraft.from_case(case).with_batch(timestamp_label())
    stocked = _stocked_lines(case, draft)
    # Taken before any earlier document is seeded, so stock a challan takes in is checked as well.
    before = stock.snapshot(stocked)
    draft = _with_earlier_documents(page, case, draft)

    number = bills.create(draft)

    # A bill made from a challan adds nothing more: the challan already did.
    stock.expect_received(stocked, before)
    if draft.order_number:
        bills.menu.open_purchase(PurchaseScreen.ORDER)
        bills.documents.delete_after_conversion(draft.order_number)
    if is_yes(case, "delete_bill"):
        _delete(bills, number, draft)
        stock.expect_back_to(before)
    if is_yes(case, "convert_challan"):
        bills.reconvert_to_challan(number, draft.challan_number)


def _delete(bills: PurchaseBillEntryPage, number: str, draft: PurchaseDraft) -> None:
    if draft.challan_number:
        bills.delete_with_challan(number)
    else:
        bills.delete(number)


@pytest.mark.parametrize("case", negative(CASES), ids=case_id)
def test_bill_with_invalid_input_is_refused(page_as: Callable[[Account], Page], case: DocumentCase) -> None:
    bills = PurchaseBillEntryPage(open_dashboard(page_as))

    bills.expect_refused(PurchaseDraft.from_case(case).with_batch(timestamp_label()))
