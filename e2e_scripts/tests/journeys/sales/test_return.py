"""Sale return cases (sheet `return`). A return of a bill creates that bill first."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.sale.documents.document_requests import ProductLine, request_from, wants
from pages.sale.documents.flows import (
    STORED_BILL,
    create_bill,
    fill_body,
    finish_and_save,
    open_sales_page,
    stored_case,
)
from pages.sale.documents.returns import MANUAL_RETURN, ReturnSource, SaleReturn
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


@pytest.mark.parametrize("case", cases_for("sales", "return"), ids=case_id)
def test_sale_return(sales_page: Page, case: DocumentCase) -> None:
    request = request_from(case)
    source = _return_source(sales_page, case)
    returned_lines = _returned_lines(source, request.lines)
    ledger = StockLedger(sales_page)
    stock = ledger.snapshot(() if case.is_negative else returned_lines)
    sale_return = SaleReturn(sales_page)
    sale_return.open_new()
    sale_return.choose_party_for_return(request.party, source)
    sale_return.enter_date(request.day)
    if not request.is_dated_today:
        sale_return.expect_date_rejected()
        return
    if source.kind == "Single":
        sale_return.expect_product_loaded(0)
    else:
        fill_body(sale_return, request)
    if request.has_unsellable_quantity:
        return  # the warning for the quantity was already asserted while entering the line
    number = finish_and_save(sale_return, case, request)
    if not case.is_negative:
        ledger.expect_returned(stock, returned_lines)
        _delete_if_asked(sale_return, case, number)
        if wants(case, "delete_return"):
            ledger.expect_restored(stock)


def _return_source(page: Page, case: DocumentCase) -> ReturnSource:
    if case.inputs.get("return_type") != "Single":
        return MANUAL_RETURN
    return ReturnSource("Single", create_bill(page))


def _returned_lines(source: ReturnSource, own_lines: tuple[ProductLine, ...]) -> tuple[ProductLine, ...]:
    """A single-bill return gives back the bill's lines; a manual return gives back its own."""
    if source.kind == "Single":
        return request_from(stored_case("bill", STORED_BILL)).lines
    return own_lines


def _delete_if_asked(sale_return: SaleReturn, case: DocumentCase, number: str) -> None:
    if wants(case, "delete_return"):
        sale_return.delete(number)
