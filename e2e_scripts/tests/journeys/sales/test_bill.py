"""Sale bill cases (sheet `bill`). Bills taken from an order or challan create that document first."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.document_requests import (
    DocumentRequest,
    ProductLine,
    request_from,
    uses_earlier_document,
    wants,
)
from pages.sale.documents.flows import (
    STORED_CHALLAN,
    create_challan,
    create_order,
    fill_body,
    finish_and_save,
    open_sales_page,
    start_document,
    stored_case,
)
from pages.sale.documents.order import SaleOrder
from pages.sale.documents.pending_windows import Templates
from pages.sale.documents.stock import StockLedger
from test_data.document_cases import DocumentCase, case_id, cases_for

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.fixture
def sales_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.mark.parametrize("case", cases_for("sales", "bill"), ids=case_id)
def test_sale_bill(sales_page: Page, case: DocumentCase) -> None:
    request = request_from(case)
    ledger = StockLedger(sales_page)
    sold_lines = _sold_lines(case, request)
    # Taken before any earlier document is made, so stock a challan takes out is checked as well.
    stock = ledger.snapshot(sold_lines)
    order_number = create_order(sales_page) if uses_earlier_document(case, "order_number") else ""
    challan_number = create_challan(sales_page) if uses_earlier_document(case, "challan_number") else ""
    templates = Templates(order=order_number, challan=challan_number)
    bill = SaleBillDocument(sales_page)
    start_document(bill, request, templates)
    if not case.is_negative and not templates.is_empty:
        _price_loaded_lines(bill, case)
    if not request.is_dated_today:
        bill.expect_date_rejected()
        return
    if templates.is_empty:
        fill_body(bill, request)
    if request.has_unsellable_quantity:
        return  # the warning for the quantity was already asserted while entering the line
    number = finish_and_save(bill, case, request)
    if case.is_negative:
        return
    # A bill made from a challan takes nothing more out: the challan already did.
    ledger.expect_sold(stock, sold_lines)
    _follow_up(bill, case, (number, order_number, challan_number))
    if wants(case, "delete_bill"):
        ledger.expect_restored(stock)


def _sold_lines(case: DocumentCase, request: DocumentRequest) -> tuple[ProductLine, ...]:
    """Lines whose stock the bill, or the challan it is made from, takes out; none for a refused bill."""
    if case.is_negative:
        return ()
    if uses_earlier_document(case, "challan_number"):
        return request_from(stored_case("challan", STORED_CHALLAN)).lines
    return request.lines


def _price_loaded_lines(bill: SaleBillDocument, case: DocumentCase) -> None:
    for row, line in enumerate(request_from(case).lines):
        bill.enter_price(row, line)


def _follow_up(bill: SaleBillDocument, case: DocumentCase, saved: tuple[str, str, str]) -> None:
    number, order_number, challan_number = saved
    if order_number:
        SaleOrder(bill.page).delete_converted(order_number)
    if wants(case, "delete_bill") and challan_number:
        bill.delete_with_challan(number)
    elif wants(case, "delete_bill"):
        bill.delete(number)
    if wants(case, "convert_challan"):
        bill.convert_back_to_challan(number, challan_number)
