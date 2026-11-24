"""Batch List: the "Select Batch" window that lists one item's batches and their closing quantity.

Component `ProcessInBatchComponent` (childcomponents/processinbatch.component.ts). Its grid columns are
`batchName` and the closing quantity (`OpeningQuantity`, or `multiunitdetails` with two-unit quantities),
processinbatch.component.ts:140-142. Zero-stock batches are filtered out (processinbatch.component.ts:575-597)
until "ShowAll Batch" (key F7, `Availblestock`, processinbatch.component.ts:983-993, :1031-1034) is used. A
search that matches nothing shows "<text> Not Found!" (UtililityComponent/Validation/not.found.component.ts).

Two doors lead to the window: Item list > F4 > "Batch List" (itemmaster.component.ts:3011-3045, offered only
when the company works in style 2, or style 1 with parameter inventory, itemmaster.component.ts:2546), and the
batch cell of a document line (the same window, `isModelOpenFromOtherWindow`, ts:373).
This reader uses the second door because it is open in every working style: a new sale challan is opened,
the item is picked, the batch cell is entered, and the challan is left unsaved. Nothing is written.
"""

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document_requests import parse_decimal
from pages.sale.documents.item_grid import BATCH
from pages.sale.documents.selection_window import SelectionWindow
from pages.stock.search_typing import type_search

PARTY = "Cash Account"
WINDOW_TIMEOUT_MS = 20_000
BATCH_NAME = "batchName"
CLOSING_QUANTITY = '[col-id="OpeningQuantity"], [col-id="multiunitdetails"]'
SHOW_ALL_BATCHES_KEY = "F7"


class BatchNotListedError(AssertionError):
    def __init__(self, batch: str, listed: tuple[str, ...]) -> None:
        super().__init__(f'Batch "{batch}" is not in the Batch List; it lists {listed}')


@dataclass(frozen=True)
class BatchRow:
    name: str
    quantity: Decimal


@dataclass(frozen=True)
class SearchOutcome:
    rows_listed: int
    not_found_shown: bool


class BatchList(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._challan = SaleChallan(page)
        self._selection = SelectionWindow(page)

    def batches_with_stock(self, product: str) -> dict[str, Decimal]:
        """Batch name to closing quantity for the batches shown by default (stock above zero), in the
        order the window lists them. Rows with the same name are added up."""
        self._open(product)
        rows = self._read_rows()
        self._close()
        return _by_name(rows)

    def all_batches(self, product: str) -> dict[str, Decimal]:
        """Every batch, zero-stock ones too, after "ShowAll Batch". Rows with the same name are added up."""
        self._open(product)
        self._show_all()
        rows = self._read_rows()
        self._close()
        return _by_name(rows)

    def quantity_of(self, product: str, batch: str) -> Decimal:
        """One batch's closing quantity; a batch missing even with all batches shown is an error."""
        batches = self.all_batches(product)
        if batch not in batches:
            raise BatchNotListedError(batch, tuple(batches))
        return batches[batch]

    def search_for(self, product: str, text: str) -> SearchOutcome:
        """Types `text` into the window's search box and reports what the window then shows."""
        self._open(product)
        type_search(self._window.get_by_role("searchbox"), text)
        outcome = SearchOutcome(self._rows.count(), self._not_found(text).is_visible())
        self._close()
        return outcome

    def _open(self, product: str) -> None:
        self._challan.open_new()
        self._challan.choose_party(PARTY)
        self._challan.grid.select_product(0, product)
        if not self._selection.is_shown():
            cell = self._challan.grid.cell(0, BATCH)
            expect(cell).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
            cell.press("Enter")
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        listed = self._window.locator(f'[col-id="{BATCH_NAME}"]').first
        expect(listed).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def _show_all(self) -> None:
        self.page.keyboard.press(SHOW_ALL_BATCHES_KEY)
        self._challan.screen.wait_for_loader()

    def _read_rows(self) -> list[BatchRow]:
        return [
            BatchRow(
                self._rows.nth(index).locator(f'[col-id="{BATCH_NAME}"]').inner_text().strip(),
                parse_decimal(self._rows.nth(index).locator(CLOSING_QUANTITY).first.inner_text()),
            )
            for index in range(self._rows.count())
        ]

    def _close(self) -> None:
        self._selection.close()
        self._challan.leave_to_list()

    def _not_found(self, text: str) -> Locator:
        return self._window.get_by_text(f"{text} Not Found!")

    @property
    def _rows(self) -> Locator:
        return self._window.locator(".ag-center-cols-container .ag-row")

    @property
    def _window(self) -> Locator:
        # Why CSS: the window is a Bootstrap modal around the custom element `processin-batch`.
        return self.page.locator("ngb-modal-window").filter(has=self.page.locator("processin-batch")).last


def _by_name(rows: list[BatchRow]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for row in rows:
        totals[row.name] = totals.get(row.name, Decimal(0)) + row.quantity
    return totals
