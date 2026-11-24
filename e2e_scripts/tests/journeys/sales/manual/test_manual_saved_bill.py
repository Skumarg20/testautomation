"""Manual cases 22, 32, 109, 110, 113, 153: changing, cancelling and printing a saved bill.

Each test saves its own bill (item 44646015, quantities 1 and 2 at rate 100), reopens it from the sale bill
list (`DocumentList.open_for_change`) and is deleted afterwards by the `saved_bills` fixture. "Amount
Calculation On Billing" is held at Rate*Qty so every amount is quantity x rate (`dataCalculation.ts:750-757`).
Expected figures are that arithmetic. The print preview is the PDF the server builds for the bill
(`PrintTemplate/PrintTemplateExport`, trxnprint.component.ts:322-386); nothing goes to a printer.
Stock is read from the item list, as the ported TC_SM_001 does (`pages/sale/documents/stock.py`).
"""

from decimal import Decimal

import pytest

from pages.accounting.outstanding.document_list import DocumentList
from pages.notifications_export.pdf_text import PdfText
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.stock import StockLedger
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, ITEM_REPEATED, HeldOptions
from pages.sale.manual.pharma_bill import BATCH, ITEM, PARTY, RATE, PharmaBill
from pages.sale.manual.saved_bills import SavedBills

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-modification"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)
TWO = Decimal(2)
THREE = Decimal(3)
FIVE = Decimal(5)
NEW_RATE = Decimal(90)
CURRENCY_SHOWN = "{:.2f}"


def sold(quantity: Decimal) -> tuple[ProductLine, ...]:
    return (ProductLine(ITEM, BATCH, quantity, RATE),)


@pytest.fixture
def saved_number(options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills) -> str:
    """A saved bill with two rows (quantity 1 and 2); the bill screen is closed again."""
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    options.hold(ITEM_REPEATED, "No")
    bill.start()
    bill.add_line(0, ONE)
    bill.add_line(1, TWO)
    return saved_bills.save(bill)


def test_deleting_an_item_from_a_saved_bill_updates_the_bill(bill: PharmaBill, saved_number: str) -> None:
    """Row 22: after the row is deleted and the bill saved, the reopened bill has one row and its total."""
    bill.reopen(saved_number)
    bill.delete_row(2)
    bill.save_changes()

    bill.reopen(saved_number)

    bill.expect_quantities([ONE])
    bill.expect_gross(ONE * RATE)


def test_changing_a_saved_quantity_moves_the_stock_with_it(
    bill: PharmaBill, saved_bills: SavedBills, options: HeldOptions
) -> None:
    """Row 109: a bill of 1 changed to 3 takes 3 out of the item's stock in all, and shows 3 x 100."""
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    ledger = StockLedger(bill.page)
    before = ledger.snapshot(sold(ONE))
    bill.start()
    bill.add_line(0, ONE)
    number = saved_bills.save(bill)

    bill.reopen(number)
    bill.change_quantity(0, THREE)
    bill.save_changes()

    ledger.expect_sold(before, sold(THREE))
    bill.reopen(number)
    bill.expect_gross(THREE * RATE)


def test_changing_a_saved_rate_changes_the_amount(bill: PharmaBill, saved_number: str) -> None:
    """Row 110: both rows at the new rate of 90 (the app asks to accept a rate below the master's)."""
    bill.reopen(saved_number)
    for row in (0, 1):
        bill.type_rate(row, f"{NEW_RATE:f}")
        bill.accept_low_rate_if_asked()
    bill.save_changes()

    bill.reopen(saved_number)

    bill.expect_gross((ONE + TWO) * NEW_RATE)


def test_leaving_a_changed_bill_without_saving_keeps_the_original(
    bill: PharmaBill, saved_number: str
) -> None:
    """Row 113: after Close and Yes the reopened bill still has quantities 1 and 2."""
    bill.reopen(saved_number)
    bill.change_quantity(0, FIVE)
    bill.close_with_escape_button()
    bill.expect_discard_prompt()
    bill.confirm_discard()

    bill.reopen(saved_number)

    bill.expect_quantities([ONE, TWO])


def test_printed_bill_carries_the_grid_rows(
    options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills
) -> None:
    """Row 32: the preview shows the batch and each row's amount (100.00 and 200.00) as entered."""
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    options.hold(ITEM_REPEATED, "No")
    bill.start()
    bill.add_line(0, ONE)
    bill.add_line(1, TWO)

    pdf = saved_bills.around_preview(bill)

    page = PdfText(pdf).pages()[0]
    assert page.shows(BATCH)
    assert page.shows(CURRENCY_SHOWN.format(ONE * RATE))
    assert page.shows(CURRENCY_SHOWN.format(TWO * RATE))


def test_print_after_a_modification_shows_the_latest_data(
    bill: PharmaBill, saved_number: str, saved_bills: SavedBills
) -> None:
    """Row 153: the first row changed from 1 to 3 prints as 300.00."""
    bill.reopen(saved_number)
    bill.change_quantity(0, THREE)

    pdf = bill.save_and_preview()

    assert PdfText(pdf).pages()[0].shows(CURRENCY_SHOWN.format(THREE * RATE))
    assert saved_number in DocumentList(bill.page, SaleBillDocument.menu).numbers_for(PARTY)
