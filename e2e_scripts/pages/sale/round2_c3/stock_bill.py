"""A pharma sale bill that sells the item a test made (`OwnedStock`), to a customer it made or any party.

The grid is the document grid every sale test uses: product by item code, batch by name, quantity typed, the
rate left as the app picks it unless a test types one. Nothing here saves; `PartyBills` is the one place that
does, and it remembers each new bill's number so the test's fixture deletes it.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.accounting.outstanding.document_desk import UnexpectedNewDocumentsError
from pages.accounting.outstanding.document_list import DocumentList
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.accounting.waiting import appears_within
from pages.dashboard_page import DashboardPage
from pages.masters.master_records import MasterRecords
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.flows import start_document
from pages.sale.documents.item_grid import BATCH, FIRST_DISCOUNT, PRICE
from pages.sale.documents.screen import exact_text
from pages.sale.manual.pharma_bill import PharmaBill, request_on
from pages.sale.round2_c3.owned_stock import OwnedItem
from test_data.masters import MasterDataFactory


@dataclass(frozen=True)
class StockLine:
    """One grid line: an owned item in one of its batches."""

    item: OwnedItem
    batch: str
    quantity: Decimal


BATCH_WINDOW_WAIT_MS = 2_000
BATCH_WINDOW_TIMEOUT_MS = 10_000
BATCH_NAME_COLUMN = '[col-id="batchName"]'
FREE = "free"
BARCODE = "tmp_barcode"


class OwnedCustomer:
    """A customer ledger made through Master > Ledger, removed afterwards (after the bills that name it)."""

    def __init__(self, page: Page, run_id: str) -> None:
        self._page = page
        self._records = MasterRecords(page, MasterDataFactory(run_id))
        self.name = ""

    def create(self) -> str:
        DashboardPage(self._page).open()
        self.name = self._records.saved_customer().name
        PartyAvailability(self._page).wait_until_selectable(self.name)
        return self.name

    def remove(self) -> None:
        DashboardPage(self._page).open()
        self._records.delete_all()


class StockBill:
    """Steps on a `PharmaBill` for a line of an owned item."""

    def __init__(self, bill: PharmaBill) -> None:
        self.bill = bill
        self.grid = bill.document.grid

    def start_for(self, party: str) -> None:
        """A new bill dated today with `party` chosen (Select Party answered by name)."""
        request = request_on(date.today())
        start_document(self.bill.document, replace(request, party=party))

    def pick(self, row: int, line: StockLine) -> None:
        """Product, batch and quantity; the rate is whatever the app fills in."""
        self.grid.select_product(row, line.item.code)
        self.grid.choose_batch(row, line.batch)
        self.grid.enter_quantity(row, line.quantity)

    def picked_rate(self, row: int) -> Decimal:
        return self.grid.displayed_price(row)

    def batch_order(self, item: OwnedItem) -> list[str]:
        """Picks the item on row 0 and returns its batches in the order the batch window lists them. The
        window is closed again; the line stays unfinished."""
        self.grid.select_product(0, item.code)
        names = self._batch_names
        if not appears_within(names.first, BATCH_WINDOW_WAIT_MS):
            self.grid.cell(0, BATCH).press("Enter")
        expect(names.first).to_be_visible(timeout=BATCH_WINDOW_TIMEOUT_MS)
        shown = [text.strip() for text in names.all_inner_texts()]
        self.bill.page.keyboard.press("Escape")
        return [name for name in shown if name in item.batch_names]

    def try_batch(self, row: int, name: str) -> None:
        """Clicks the batch in the batch window of `row` without waiting for the window to close, for a batch
        the bill may refuse (an alert then keeps the window open)."""
        if not appears_within(self._batch_names.first, BATCH_WINDOW_WAIT_MS):
            self.grid.cell(row, BATCH).press("Enter")
        expect(self._batch_names.first).to_be_visible(timeout=BATCH_WINDOW_TIMEOUT_MS)
        self._batch_names.filter(has_text=exact_text(name)).first.click()

    def scan_barcode(self, row: int, barcode: str) -> None:
        """Types a barcode in the row's barcode cell and presses Enter, as a scanner does."""
        cell = self.grid.cell(row, BARCODE)
        cell.click()
        cell.press_sequentially(barcode)
        cell.press("Enter")

    def type_free(self, row: int, text: str) -> None:
        """Types `text` in the Free cell and presses Enter."""
        cell = self.grid.cell(row, FREE)
        cell.click()
        editor = cell.locator("input")
        editor.press_sequentially(text)
        editor.press("Enter")

    def type_discount(self, row: int, percent: Decimal) -> None:
        """Types the first item discount of `row` and presses Enter."""
        self.grid.enter_discount(row, FIRST_DISCOUNT, percent)

    def free_shown(self, row: int) -> str:
        return self.grid.cell(row, FREE).inner_text().strip()

    def type_rate(self, row: int, rate: Decimal) -> None:
        """Types `rate` in the rate cell and presses Enter, which `netrateask.component.ts` reads (with the
        right arrow) to check the typed value."""
        cell = self.grid.cell(row, PRICE)
        cell.click()
        editor = cell.locator("input")
        editor.press("Control+A")
        editor.press_sequentially(format(rate, "f"))
        editor.press("Enter")

    @property
    def _batch_names(self) -> Locator:
        return self.bill.page.locator(BATCH_NAME_COLUMN)


class PartyBills:
    """Saves the open bill and remembers the new number under `party`; `delete_all` removes every one."""

    def __init__(self, page: Page, party: str) -> None:
        self._page = page
        self._party = party
        self._list = DocumentList(page, SaleBillDocument.menu)
        self._numbers: list[str] = []

    def save(self, save_steps: Callable[[], None]) -> str:
        before = set(self._list.numbers_for(self._party))
        save_steps()
        new = sorted(set(self._list.numbers_for(self._party)) - before)
        self._numbers.extend(new)
        if len(new) != 1:
            raise UnexpectedNewDocumentsError(self._party, new)
        return new[0]

    def delete_all(self) -> None:
        document = SaleBillDocument(self._page)
        for number in reversed(self._numbers):
            document.delete(number)
        self._numbers.clear()
