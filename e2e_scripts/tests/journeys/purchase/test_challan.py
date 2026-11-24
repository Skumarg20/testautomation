"""Purchase challans: stock rises by quantity plus free quantity; deleting gives it back."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.purchase.documents.challan_page import PurchaseChallanPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.drafts import PurchaseDraft, is_yes, needs
from pages.purchase.documents.item_stock import ItemStock
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.seed_documents import seed_order
from pages.purchase.documents.support import negative, open_dashboard, positive
from test_data.document_cases import DocumentCase, case_id, cases_for

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

CASES = cases_for("purchase", "challan")


@pytest.mark.parametrize("case", positive(CASES), ids=case_id)
def test_challan_receives_stock(page_as: Callable[[Account], Page], case: DocumentCase) -> None:
    page = open_dashboard(page_as)
    challans = PurchaseChallanPage(page)
    stock = ItemStock(page)
    draft = PurchaseDraft.from_case(case).with_batch(timestamp_label())
    if needs(case, "order"):
        draft = draft.from_order(seed_order(page))
    before = stock.snapshot(draft.lines)

    number = challans.create(draft)

    stock.expect_received(draft.lines, before)
    if draft.order_number:
        challans.menu.open_purchase(PurchaseScreen.ORDER)
        challans.documents.delete_after_conversion(draft.order_number)
    if is_yes(case, "delete_challan"):
        challans.delete(number)
        stock.expect_back_to(before)


@pytest.mark.parametrize("case", negative(CASES), ids=case_id)
def test_challan_with_invalid_input_is_refused(
    page_as: Callable[[Account], Page], case: DocumentCase
) -> None:
    challans = PurchaseChallanPage(open_dashboard(page_as))

    challans.expect_refused(PurchaseDraft.from_case(case).with_batch(timestamp_label()))
