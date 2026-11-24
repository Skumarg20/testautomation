"""Sale checklist rows 24 and 35 (quotation loading and the document chain) and 36 (print formats).

Quotation, order, challan and bill are built for the owned customer and item; the pending windows
(`pending_windows.py`) offer each earlier document when the party is chosen (`getLoadPendingQuotation`,
`getloadPendingOrders`, `getloadPendingChallans`, processout:6030-6036). A converted document cannot be
deleted (`SaleOrder.delete_converted`), so the chain test is marked permanent.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from pages.accounting.waiting import appears_within
from pages.notifications_export.pdf_text import PdfText
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document_requests import DocumentRequest, ProductLine
from pages.sale.documents.flows import start_document
from pages.sale.documents.order import SaleOrder
from pages.sale.documents.pending_windows import Templates
from pages.sale.manual.pharma_bill import request_on
from pages.sale.round2_c3.owned_stock import BatchSpec, OwnedItem, StockSpec
from pages.sale.round2_c3.print_formats import PrintFormats
from pages.sale.round2_c3.quotation import SaleQuotation
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

QUANTITY = Decimal(2)
RATE = Decimal(130)
ONE_BATCH = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),))


def quotation_line(item: OwnedItem) -> ProductLine:
    return ProductLine(item.code, "", QUANTITY, RATE)


QUOTATION_WINDOW_WAIT_MS = 5_000


def request_for(desk: SaleDesk) -> DocumentRequest:
    return replace(request_on(date.today()), party=desk.customer)


def save_quotation(desk: SaleDesk, item: OwnedItem) -> str:
    page = desk.bill.bill.page
    quotation = SaleQuotation(page)
    start_document(quotation, request_for(desk))
    quotation.add_line(0, quotation_line(item))
    number = quotation.document_number()
    quotation.save()
    quotation.expect_saved()
    return number


def test_a_saved_quotation_is_offered_when_its_party_opens_a_bill(desk: SaleDesk) -> None:
    """Row 24: choosing the party of a saved quotation on a new bill shows the Pending Quotation window with
    it; the quotation is deleted afterwards (nothing was converted)."""
    item = desk.make_stock(ONE_BATCH)
    number = save_quotation(desk, item)
    try:
        page = desk.bill.bill.page
        bill = SaleBillDocument(page)
        bill.open_new()
        bill.header.choose_party(desk.customer)

        window = page.locator("pending-challan").filter(has_text="Pending Quotation").filter(has_text=number)
        assert appears_within(window, QUOTATION_WINDOW_WAIT_MS)
        bill.pending.close_all()
        desk.bill.bill.leave_without_saving()
    finally:
        SaleQuotation(desk.bill.bill.page).delete(number)


@pytest.mark.permanent(
    "a quotation and an order that were converted cannot be deleted and stay in the QA company"
)
def test_quotation_order_challan_bill_chain_keeps_the_lines(desk: SaleDesk) -> None:
    """Row 35: the quotation's 2 pieces at 130 load into an order, the order into a challan, the challan
    into a bill; the quantity and rate on the bill are those of the quotation."""
    item = desk.make_stock(ONE_BATCH)
    page = desk.bill.bill.page
    quotation_number = save_quotation(desk, item)
    order = SaleOrder(page)
    start_document(order, request_for(desk), Templates(quote=quotation_number))
    order_number = order.document_number()
    order.save()
    order.expect_saved()
    challan = SaleChallan(page)
    start_document(challan, request_for(desk), Templates(order=order_number))
    challan_number = challan.document_number()
    challan.save()
    challan.expect_saved()
    bill = SaleBillDocument(page)
    start_document(bill, request_for(desk), Templates(challan=challan_number))

    assert bill.grid.quantity_in_grid(0) == QUANTITY
    assert bill.grid.displayed_price(0) == RATE
    bill.leave_to_list()


def test_every_print_format_shows_the_bill_number(desk: SaleDesk) -> None:
    """Row 36: the Print window's Select Format lists the company's templates; previewing each gives a PDF
    that carries the saved bill's number."""
    item = desk.make_stock(ONE_BATCH)
    desk.sell(StockLine(item, item.batch_names[0], Decimal(1)))
    formats = PrintFormats(desk.bill.bill.document)

    number = desk.bills.save(formats.save_and_preview_every_format)

    assert formats.pdfs
    for name, pdf in formats.pdfs.items():
        assert PdfText(pdf).pages()[0].shows(number), name
