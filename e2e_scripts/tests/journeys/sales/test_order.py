"""Sale order cases (sheet `order`). Each case creates what it needs and follows its own row."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.sale.documents.document_requests import request_from, wants
from pages.sale.documents.flows import fill_body, finish_and_save, open_sales_page, start_document
from pages.sale.documents.order import SaleOrder
from test_data.document_cases import DocumentCase, case_id, cases_for

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.fixture
def order(page_as: Callable[[Account], Page]) -> SaleOrder:
    return SaleOrder(open_sales_page(page_as))


@pytest.mark.parametrize("case", cases_for("sales", "order"), ids=case_id)
def test_sale_order(order: SaleOrder, case: DocumentCase) -> None:
    request = request_from(case)
    start_document(order, request)
    if not request.is_dated_today:
        order.expect_date_rejected()
        return
    fill_body(order, request)
    if request.has_unsellable_quantity:
        return  # the warning for the quantity was already asserted while entering the line
    number = finish_and_save(order, case, request)
    _follow_up(order, case, number)


def _follow_up(order: SaleOrder, case: DocumentCase, number: str) -> None:
    if wants(case, "convert_bill"):
        order.convert_to_bill(number)
    if wants(case, "delete_order"):
        order.delete(number)
    if wants(case, "close_order"):
        order.close(number)
