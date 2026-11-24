"""Sale documents saved for the stock tests: a challan, a bill, a return, a return challan and a stock issue.

Every request is for item 44646015 (the pharma sales and purchase test item) at price 100 with the bill
discount the stored cases use, so the screens behave as in the ported sale cases; only the batch and the
quantity change. The stored cases give the party, patient, doctor and address.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from playwright.sync_api import Page

from pages.purchase.documents.line_items import STANDARD_ITEM_CODE
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document import SaleDocument
from pages.sale.documents.document_requests import DocumentRequest, ProductLine, request_from
from pages.sale.documents.flows import fill_body, finish_and_save, start_document, stored_case
from pages.sale.documents.pending_windows import Templates
from pages.sale.documents.returns import MANUAL_RETURN, SaleReturn
from pages.stock.sale_impact.return_challan import SaleReturnChallan
from pages.stock.sale_impact.stock_issue import StockIssue
from pages.stock.sale_impact.zero_batch_return import ZeroStockReturn

PRODUCT = STANDARD_ITEM_CODE
SALE_PRICE = Decimal(100)
CHALLAN_CASE = ("challan", "TC_SM_001")
BILL_CASE = ("bill", "TC_SM_001")
RETURN_CASE = ("return", "TC_SM_003")


def sale_request(batch: str, quantity: Decimal) -> DocumentRequest:
    """The stored challan request with its one line replaced by `quantity` of `batch`."""
    stored = request_from(stored_case(*CHALLAN_CASE))
    line = ProductLine(product=PRODUCT, batch=batch, quantity=quantity, price=SALE_PRICE)
    return replace(stored, lines=(line,))


def dated(request: DocumentRequest, day: date) -> DocumentRequest:
    return replace(request, day=day)


def save_challan(page: Page, request: DocumentRequest) -> str:
    return _save(SaleChallan(page), CHALLAN_CASE, request)


def save_stock_issue(page: Page, request: DocumentRequest) -> str:
    return _save(StockIssue(page), CHALLAN_CASE, request)


def save_return_challan(page: Page, request: DocumentRequest) -> str:
    return _save(SaleReturnChallan(page), CHALLAN_CASE, request)


def save_bill(page: Page, request: DocumentRequest) -> str:
    return _save(SaleBillDocument(page), BILL_CASE, request)


def save_bill_from_challan(page: Page, challan_number: str, request: DocumentRequest) -> str:
    """A bill that takes over the challan's lines; the lines are priced as the stored bill cases do."""
    bill = SaleBillDocument(page)
    start_document(bill, request, Templates(challan=challan_number))
    for row, line in enumerate(request.lines):
        bill.enter_price(row, line)
    return finish_and_save(bill, stored_case(*BILL_CASE), request)


def save_manual_return(page: Page, request: DocumentRequest) -> str:
    return _save_return(SaleReturn(page), request)


def save_return_of_empty_batch(page: Page, request: DocumentRequest) -> str:
    """A manual return whose batch has no stock left, so the batch is picked with all batches shown."""
    return _save_return(ZeroStockReturn(page), request)


def _save_return(sale_return: SaleReturn, request: DocumentRequest) -> str:
    sale_return.open_new()
    sale_return.choose_party_for_return(request.party, MANUAL_RETURN)
    sale_return.enter_date(request.day)
    fill_body(sale_return, request)
    return finish_and_save(sale_return, stored_case(*RETURN_CASE), request)


def _save(document: SaleDocument, case_key: tuple[str, str], request: DocumentRequest) -> str:
    start_document(document, request)
    fill_body(document, request)
    return finish_and_save(document, stored_case(*case_key), request)
