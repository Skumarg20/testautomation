"""J21 sale bill Print window (specs/notifications-export.md, NE-26). The test's own customer and bill
(deleted in teardown); Preview opens the PDF, Close leaves the bill saved, nothing goes to a printer."""

from datetime import date

import pytest

from pages.notifications_export.pdf_text import PdfPage, PdfText
from test_data.notifications_export import PreviewedBill

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

BILL_DATE_FORMAT = "%d-%m-%Y"


@pytest.fixture
def preview(previewed_bill: PreviewedBill) -> PdfPage:
    """The first page of the preview. The bill is saved once Close was pressed: its number is read back from
    the sale bill list after the Print window closed (`DocumentDesk._saved_number`)."""
    return PdfText(previewed_bill.preview_pdf).pages()[0]


def test_preview_shows_the_bill_number(preview: PdfPage, previewed_bill: PreviewedBill) -> None:
    """NE-26: the preview is of the bill just saved."""
    assert preview.shows(previewed_bill.number)


def test_preview_shows_the_bill_date(preview: PdfPage) -> None:
    """NE-26 (MB-037864): the date is printed dd-mm-yyyy, as on screen."""
    assert preview.shows(date.today().strftime(BILL_DATE_FORMAT))


def test_preview_shows_the_bill_total(preview: PdfPage, previewed_bill: PreviewedBill) -> None:
    """NE-26: the total is the bill's amount (one 0% GST line, so no tax is added)."""
    assert preview.shows(f"{previewed_bill.amount:.2f}")
