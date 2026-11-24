"""Purchase orders: create, then delete, convert or close; and the refusals."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.purchase.documents.drafts import PurchaseDraft, is_yes
from pages.purchase.documents.order_page import PurchaseOrderPage
from pages.purchase.documents.support import negative, open_dashboard, positive
from test_data.document_cases import DocumentCase, case_id, cases_for

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

CASES = cases_for("purchase", "order")


@pytest.mark.parametrize("case", positive(CASES), ids=case_id)
def test_order_is_saved_then_followed_up(page_as: Callable[[Account], Page], case: DocumentCase) -> None:
    orders = PurchaseOrderPage(open_dashboard(page_as))

    number = orders.create(PurchaseDraft.from_case(case))

    if is_yes(case, "convert_bill"):
        orders.convert_to_bill(number)
    if is_yes(case, "close_order"):
        orders.close_order(number)
    if is_yes(case, "delete_order"):
        orders.delete(number)


@pytest.mark.parametrize("case", negative(CASES), ids=case_id)
def test_order_with_invalid_input_is_refused(page_as: Callable[[Account], Page], case: DocumentCase) -> None:
    orders = PurchaseOrderPage(open_dashboard(page_as))

    orders.expect_refused(PurchaseDraft.from_case(case))
