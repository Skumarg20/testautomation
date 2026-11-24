"""Sale challan cases (sheet `challan`). A challan taken from an order creates that order first."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document_requests import request_from, uses_earlier_document, wants
from pages.sale.documents.flows import (
    create_order,
    fill_body,
    finish_and_save,
    open_sales_page,
    start_document,
)
from pages.sale.documents.order import SaleOrder
from pages.sale.documents.pending_windows import Templates
from pages.sale.documents.stock import StockLedger, StockSnapshot
from test_data.document_cases import DocumentCase, case_id, cases_for

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.fixture
def sales_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.mark.parametrize("case", cases_for("sales", "challan"), ids=case_id)
def test_sale_challan(sales_page: Page, case: DocumentCase) -> None:
    request = request_from(case)
    order_number = create_order(sales_page) if uses_earlier_document(case, "order_number") else ""
    ledger = StockLedger(sales_page)
    stock = ledger.snapshot(() if case.is_negative else request.lines)
    challan = SaleChallan(sales_page)
    start_document(challan, request, Templates(order=order_number))
    if not request.is_dated_today:
        challan.expect_date_rejected()
        return
    if not order_number:
        fill_body(challan, request)
    if request.has_unsellable_quantity:
        return  # the warning for the quantity was already asserted while entering the line
    number = finish_and_save(challan, case, request)
    if not case.is_negative:
        _check_positive_outcome(challan, case, (number, order_number, stock))


def _check_positive_outcome(
    challan: SaleChallan, case: DocumentCase, saved: tuple[str, str, StockSnapshot]
) -> None:
    number, order_number, stock = saved
    ledger = StockLedger(challan.page)
    ledger.expect_sold(stock, request_from(case).lines)
    if order_number:
        SaleOrder(challan.page).delete_converted(order_number)
    if wants(case, "convert_bill"):
        challan.convert_to_bill(number)
    if wants(case, "delete_order"):
        challan.delete(number)
        ledger.expect_restored(stock)
