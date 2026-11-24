"""Bills a test saved: their numbers are read from the sale bill list afterwards, and all are deleted.

The number shown before a save can be taken by another user's save in between (OA-010, 2026-10-09), so the
new number is the one the list gains for the party, as `DocumentDesk._saved_number` does for garments.
"""

from collections.abc import Callable

from playwright.sync_api import Page

from pages.accounting.outstanding.document_desk import UnexpectedNewDocumentsError
from pages.accounting.outstanding.document_list import DocumentList
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.manual.pharma_bill import PARTY, PharmaBill


class SavedBills:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._numbers: list[str] = []
        self._list = DocumentList(page, SaleBillDocument.menu)

    def save(self, bill: PharmaBill) -> str:
        return self.around(bill.save_and_confirm)

    def around(self, save_steps: Callable[[], None]) -> str:
        """Runs the steps that save the open bill and returns the new bill's number.

        The number is remembered before anything can fail, so the bill is deleted afterwards either way."""
        before = set(self._list.numbers_for(PARTY))
        save_steps()
        new = sorted(set(self._list.numbers_for(PARTY)) - before)
        self._numbers.extend(new)
        if len(new) != 1:
            raise UnexpectedNewDocumentsError(PARTY, new)
        return new[0]

    def around_preview(self, bill: PharmaBill) -> bytes:
        """Saves the open bill, previews it in the Print window, returns the PDF; the bill is remembered."""
        previews: list[bytes] = []
        self.around(lambda: previews.append(bill.save_and_preview()))
        return previews[0]

    def forget(self, number: str) -> None:
        """For a bill the test itself deleted."""
        self._numbers.remove(number)

    def delete_all(self) -> None:
        document = SaleBillDocument(self._page)
        for number in reversed(self._numbers):
            document.delete(number)
        self._numbers.clear()
