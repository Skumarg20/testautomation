"""Sale bill rows 154 and 155: reprint one saved bill, and print several bills from the list.

The bills are saved by the test (quantity 1 and 2 at 100, "Rate*Qty"), ticked in the Sale > Bill list
and printed
with the toolbar Print button; the PDF the server returns must show each bill's own number and amount
(100.00, 200.00). See `BillListPrint` for the cited code. Print copy dialog (Control Room 4175) is
assumed off.
"""

from decimal import Decimal

import pytest

from pages.notifications_export.pdf_text import PdfText
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, ITEM_REPEATED, HeldOptions
from pages.sale.manual.pharma_bill import PARTY, PharmaBill
from pages.sale.manual.saved_bills import SavedBills
from pages.sale.round2_c4.bill_list_print import BillListPrint

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-modification"),
    pytest.mark.xdist_group("chemist-tenant"),
]

AMOUNTS = {1: "100.00", 2: "200.00"}


@pytest.fixture
def two_bills(options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills) -> tuple[str, str]:
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    options.hold(ITEM_REPEATED, "No")
    numbers = []
    for quantity in (1, 2):
        bill.start()
        bill.add_line(0, Decimal(quantity))
        numbers.append(saved_bills.save(bill))
    return numbers[0], numbers[1]


def all_text(pdf: bytes) -> str:
    return " ".join(page.text for page in PdfText(pdf).pages())


def test_reprint_of_one_bill_shows_that_bill(bill: PharmaBill, two_bills: tuple[str, str]) -> None:
    first, second = two_bills

    text = all_text(BillListPrint(bill.page).print_bills(PARTY, [first]))

    squeezed = text.replace(" ", "")
    assert first in text
    assert AMOUNTS[1] in squeezed
    assert second not in text


def test_printing_two_bills_prints_both(bill: PharmaBill, two_bills: tuple[str, str]) -> None:
    first, second = two_bills

    text = all_text(BillListPrint(bill.page).print_bills(PARTY, [first, second]))

    squeezed = text.replace(" ", "")
    assert first in text
    assert second in text
    assert AMOUNTS[1] in squeezed
    assert AMOUNTS[2] in squeezed
