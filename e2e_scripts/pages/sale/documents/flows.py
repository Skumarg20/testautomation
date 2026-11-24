"""Steps the sales tests share: open the app, fill a document, save it, build prerequisites."""

from collections.abc import Callable

from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import PHARMA_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document import SaleDocument
from pages.sale.documents.document_requests import DocumentRequest, request_from, uses_earlier_document
from pages.sale.documents.order import SaleOrder
from pages.sale.documents.pending_windows import NO_TEMPLATES, Templates
from test_data.document_cases import DocumentCase, cases_for

PHASE1_ACCOUNT: Account = "chemist"  # the pharma company, on its own QA user
MODULE = "sales"
STORED_ORDER = "TC_SM_004"
STORED_CHALLAN = "TC_SM_004"
STORED_BILL = "TC_SM_009"
EARLIER_DOCUMENT_COLUMNS = ("order_number", "challan_number")
SINGLE_RETURN = "Single"  # a return of a single bill loads that bill's lines


def open_sales_page(page_as: Callable[[Account], Page]) -> Page:
    """The ported cases use item 44646015 (batch 1231231123, with expiry): they run in the pharma company."""
    page = page_as(PHASE1_ACCOUNT)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(PHARMA_COMPANY)
    return page


def start_document(
    document: SaleDocument, request: DocumentRequest, templates: Templates = NO_TEMPLATES
) -> None:
    document.open_new()
    document.choose_party_from(request.party, templates)
    document.enter_date(request.day)


def fill_body(document: SaleDocument, request: DocumentRequest) -> None:
    document.enter_people(request)
    for row, line in enumerate(request.lines):
        document.add_line(row, line)


def finish_and_save(document: SaleDocument, case: DocumentCase, request: DocumentRequest) -> str:
    """Bill discount, invoice check, save; returns the document number read just before saving."""
    document.enter_bill_discount(request.bill_discount)
    document.verify_invoice_total(has_lines=_has_lines(case, request))
    number = document.document_number()
    document.save()
    if case.is_negative:
        document.expect_rejected()
    else:
        document.expect_saved()
    return number


def _has_lines(case: DocumentCase, request: DocumentRequest) -> bool:
    """Lines the case enters, or lines loaded from the earlier document or bill it is built from."""
    loaded = any(uses_earlier_document(case, column) for column in EARLIER_DOCUMENT_COLUMNS)
    return bool(request.lines) or loaded or case.inputs.get("return_type") == SINGLE_RETURN


def create_stored(document: SaleDocument, case: DocumentCase) -> str:
    """Create and save a document the way a stored-case row describes; returns its number."""
    request = request_from(case)
    start_document(document, request)
    fill_body(document, request)
    return finish_and_save(document, case, request)


def stored_case(sheet: str, case_id: str) -> DocumentCase:
    found = next((case for case in cases_for(MODULE, sheet) if case.id == case_id), None)
    if found is None:
        raise LookupError(f'The {MODULE} workbook has no case "{case_id}" on sheet "{sheet}"')
    return found


def create_order(page: Page) -> str:
    return create_stored(SaleOrder(page), stored_case("order", STORED_ORDER))


def create_challan(page: Page) -> str:
    return create_stored(SaleChallan(page), stored_case("challan", STORED_CHALLAN))


def create_bill(page: Page) -> str:
    return create_stored(SaleBillDocument(page), stored_case("bill", STORED_BILL))
