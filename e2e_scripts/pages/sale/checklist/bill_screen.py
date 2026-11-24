"""A new sale bill (Sale > Bill > Create) as the sale checklist walks it: header fields, party window, grid.

Selectors follow the Angular template `processout.transaction.component.html`: the date, party, bill number
and store inputs carry ids that end in a per-tab number (`txtbillDate48`), so they are found by id prefix and
the newest tab is the last match.
"""

from datetime import date

from playwright.sync_api import Locator, Page, expect

from pages.components.bill_totals import BillTotals
from pages.sale.checklist.focus import FocusProbeWalk
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.document_requests import SHARED_LINE, ProductLine, parse_decimal, request_from
from pages.sale.documents.flows import STORED_BILL, stored_case
from pages.sale.documents.item_grid import PRODUCT, QUANTITY
from pages.sale.documents.pending_windows import NO_TEMPLATES

PARTY_WINDOW_TIMEOUT_MS = 20_000
FIELD_TIMEOUT_MS = 10_000
STANDARD_LINE = ProductLine(
    product=SHARED_LINE["product_name"],
    batch=SHARED_LINE["batch"],
    quantity=parse_decimal(SHARED_LINE["product_qty"]),
    price=parse_decimal(SHARED_LINE["product_price"]),
)


def standard_party() -> str:
    """The party the workbook's stored bill case uses (a real party of the pharma company)."""
    return request_from(stored_case("bill", STORED_BILL)).party


class ChecklistBill:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.document = SaleBillDocument(page)
        self.focus = FocusProbeWalk(page)
        self.is_open = False

    def open_new(self) -> None:
        self.document.open_new()
        self.is_open = True

    def leave(self) -> None:
        BillTotals(self.page).leave_without_saving()
        self.is_open = False

    def reopen(self) -> None:
        """A fresh bill after a Control Room change, which the open bill would not pick up."""
        self.leave()
        self.open_new()

    def choose_standard_party(self) -> None:
        self.document.choose_party_from(standard_party(), NO_TEMPLATES)

    def add_standard_line(self, row: int) -> None:
        self.document.add_line(row, STANDARD_LINE)

    def enter_date(self, day: date) -> None:
        self.document.enter_date(day)

    def press_enter_on_date(self) -> None:
        self.date_input.click()
        self.date_input.press("Enter")

    def expect_warning(self) -> None:
        self.document.screen.expect_toast("warning")

    def party_window_is_open(self) -> bool:
        return self.document.selection.is_shown()

    def product_cell(self, row: int) -> Locator:
        return self.document.grid.cell(row, PRODUCT)

    def quantity_cell(self, row: int) -> Locator:
        return self.document.grid.cell(row, QUANTITY)

    def expect_grid_ready(self) -> None:
        expect(self.product_cell(0)).to_be_visible(timeout=FIELD_TIMEOUT_MS)

    @property
    def date_input(self) -> Locator:
        return self.page.locator('[id^="txtbillDate"]').last

    @property
    def party_input(self) -> Locator:
        return self.page.locator("[id^=txtLedgerName]").last

    @property
    def bill_number_input(self) -> Locator:
        return self.page.locator("[id^=txtentryNo]").last

    @property
    def store_input(self) -> Locator:
        return self.page.locator("[id^=txtStore]").last

    @property
    def pick_list(self) -> Locator:
        """The party, item or batch list window. Why CSS: it is bootstrap markup with no role or test id
        (see SelectionWindow)."""
        return self.page.locator("div.modal-dialog.modal-lg").last

    @property
    def party_window(self) -> Locator:
        return self.pick_list
