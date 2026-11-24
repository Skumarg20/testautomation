"""Purchase returns: stock falls by the returned quantity; deleting gives it back."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.purchase.documents.drafts import PurchaseDraft, ReturnMode, is_yes
from pages.purchase.documents.item_stock import ItemStock
from pages.purchase.documents.return_page import PurchaseReturnPage
from pages.purchase.documents.seed_documents import seed_bill, seed_stock_for
from pages.purchase.documents.support import negative, open_dashboard, positive
from test_data.document_cases import DocumentCase, case_id, cases_for

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

CASES = cases_for("purchase", "return")


def _returns_by_bill(case: DocumentCase) -> bool:
    return ReturnMode(case.inputs["return_type"]) is ReturnMode.SINGLE


def _return_whole_bill(page: Page, case: DocumentCase) -> None:
    returns = PurchaseReturnPage(page)
    stock = ItemStock(page)
    seeded = seed_bill(page)
    before = stock.snapshot((seeded.line,))
    draft = PurchaseDraft.from_case(case).from_bill(seeded.number)

    returns.begin(draft)
    returns.enter_entry_date(draft.entry_date)
    returns.fill_lines(draft)
    product = returns.returned_product()
    assert product.code == seeded.line.product, "the return should list the item of the bill it came from"
    number = returns.finish(draft)
    returns.expect_saved()

    stock.expect_decrease(product.code, before[product.code], product.quantity + product.free)
    if is_yes(case, "delete_return"):
        returns.delete(number)
        stock.expect_back_to(before)


def _return_by_hand(page: Page, case: DocumentCase) -> None:
    returns = PurchaseReturnPage(page)
    stock = ItemStock(page)
    draft = seed_stock_for(page, PurchaseDraft.from_case(case))
    before = stock.snapshot(draft.lines)

    number = returns.create(draft)

    for line in draft.lines:
        stock.expect_decrease(line.product, before[line.product], line.quantity + line.free)
    if is_yes(case, "delete_return"):
        returns.delete(number)
        stock.expect_back_to(before)


@pytest.mark.parametrize("case", positive(CASES), ids=case_id)
def test_return_reduces_stock(page_as: Callable[[Account], Page], case: DocumentCase) -> None:
    page = open_dashboard(page_as)
    if _returns_by_bill(case):
        _return_whole_bill(page, case)
    else:
        _return_by_hand(page, case)


@pytest.mark.parametrize("case", negative(CASES), ids=case_id)
def test_return_with_invalid_input_is_refused(page_as: Callable[[Account], Page], case: DocumentCase) -> None:
    page = open_dashboard(page_as)
    draft = seed_stock_for(page, PurchaseDraft.from_case(case))

    PurchaseReturnPage(page).expect_refused(draft)
