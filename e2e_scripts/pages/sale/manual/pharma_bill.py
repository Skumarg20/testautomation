"""A pharma-company sale bill (Sale > Bill) for the manual cases: item 44646015, batch 1231231123.

The party is Cash Account. That item and batch are the ones the ported sales cases sell (TC_SM_001..009,
`pages/sale/documents/flows.py`); the QA login has no other item with a known batch. Grid cells are read
through the document grid's col-ids.
"""

import re
from datetime import date
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.accounting.confirmation import Confirmation
from pages.accounting.outstanding.document_list import DocumentList
from pages.accounting.waiting import appears_within
from pages.components.bill_totals import BillTotals
from pages.notifications_export.bill_preview import BILL_PDF, PREVIEW
from pages.sale.chemist.sale_bill_page import SaleBillPage
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.document_requests import DocumentRequest, Person, ProductLine, plain
from pages.sale.documents.flows import start_document
from pages.sale.documents.item_grid import BATCH as BATCH_COLUMN
from pages.sale.documents.item_grid import PRICE, QUANTITY
from pages.sale.manual.bill_messages import BillMessages

PARTY = "Cash Account"
ITEM = "44646015"
BATCH = "1231231123"
RATE = Decimal(100)
PATIENT = Person("9999999999", "CASH Patient")
DOCTOR = Person("8888888888", "CASH Doctor")
ADDRESS = "Coimbatore"
GROSS_TIMEOUT_MS = 15_000
BILL_CLOSE_BUTTON = "[id^=btnEsc]"
FOOTER_SAVE_BUTTON = "[id^=btnSave]"
PROMPT_TIMEOUT_MS = 10_000
BATCH_WINDOW_LOOKUP_MS = 2_000
PREVIEW_TIMEOUT_MS = 60_000
LAST_DEAL_RATE_HEADER = "S.Rate"


def whole_number_text(value: Decimal) -> re.Pattern[str]:
    """How the grid may show a whole-number `value`: optional thousands commas, optional zero decimals."""
    digits = f"{value:f}".split(".")[0]
    return re.compile(rf"^\s*{',?'.join(digits)}(\.0+)?\s*$")


def request_on(day: date) -> DocumentRequest:
    """The header the ported TC_SM_009 case uses, for any day; no lines, no bill discount."""
    return DocumentRequest(PARTY, day, PATIENT, DOCTOR, ADDRESS, Decimal(0), ())


class PharmaBill:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.document = SaleBillDocument(page)
        self.messages = BillMessages(page)
        self._totals = BillTotals(page)

    def start(self) -> None:
        self.start_on(date.today())

    def start_on(self, day: date) -> None:
        request = request_on(day)
        start_document(self.document, request)
        self.document.enter_people(request)

    def open_with_party(self) -> None:
        """A new bill with the party chosen and the date entered; the focus is wherever the app leaves it."""
        request = request_on(date.today())
        start_document(self.document, request)

    def add_line(self, row: int, quantity: Decimal) -> None:
        self.document.add_line(row, ProductLine(ITEM, BATCH, quantity, RATE))

    def add_discounted_line(self, row: int, quantity: Decimal, percent: Decimal) -> None:
        self.document.add_line(row, ProductLine(ITEM, BATCH, quantity, RATE, discount1=percent))

    def expect_total_discount(self, expected: Decimal) -> None:
        """The footer's "Total Disc" figure (item and volume discounts) shows `expected`."""
        digits = f"{expected:f}".split(".")[0]
        shown = re.compile(rf"Total Disc[^\d]*{',?'.join(digits)}(\.0+)?\s*$")
        expect(self.page.locator("span.rb", has_text="Total Disc").first).to_have_text(
            shown, timeout=GROSS_TIMEOUT_MS
        )

    def add_line_in_batch(self, row: int, batch: str, quantity: Decimal) -> None:
        self.document.add_line(row, ProductLine(ITEM, batch, quantity, RATE))

    def batch_names_of_item(self) -> list[str]:
        """Picks the item on the first row and reads the batch window's names; the bill is left unfinished,
        so the caller leaves it without saving."""
        self.document.grid.select_product(0, ITEM)
        names = self.page.locator('[col-id="batchName"]')
        if not appears_within(names.first, BATCH_WINDOW_LOOKUP_MS):
            self.document.grid.cell(0, BATCH_COLUMN).press("Enter")
        expect(names.first).to_be_visible(timeout=PROMPT_TIMEOUT_MS)
        shown = [text.strip() for text in names.all_inner_texts()]
        self.page.keyboard.press("Escape")
        return [name for name in shown if name and not name.lower().startswith("batch")]

    def change_batch(self, row: int, batch: str) -> None:
        """Opens the batch window of a filled row and picks `batch`."""
        cell = self.document.grid.cell(row, BATCH_COLUMN)
        cell.click()
        cell.press("Enter")
        expect(self.page.locator('[col-id="batchName"]').first).to_be_visible(timeout=PROMPT_TIMEOUT_MS)
        self.document.selection.choose_cell_value(batch)

    def expect_batch_in_row(self, row: int, batch: str) -> None:
        cell = self.document.grid.cell(row, BATCH_COLUMN)
        expect(cell).to_contain_text(batch, timeout=PROMPT_TIMEOUT_MS)

    def pick_item(self, row: int, quantity: Decimal) -> None:
        """Product, batch and quantity only; the rate cell is left for the caller."""
        self.document.grid.select_product(row, ITEM)
        self.document.grid.choose_batch(row, BATCH)
        self.document.grid.enter_quantity(row, quantity)

    def type_rate(self, row: int, text: str) -> None:
        """Types `text` (empty clears the rate) into the rate cell and presses Enter."""
        cell = self.document.grid.cell(row, PRICE)
        cell.click()
        editor = cell.locator("input")
        editor.press("Control+A")
        if text:
            editor.press_sequentially(text)
        else:
            editor.press("Backspace")
        editor.press("Enter")

    def type_quantity(self, row: int, text: str) -> None:
        """Replaces the quantity of a filled row with `text` (empty clears it) and presses Enter."""
        cell = self.document.grid.cell(row, QUANTITY)
        cell.dblclick()
        editor = cell.locator("input")
        editor.press("Control+A")
        if text:
            editor.press_sequentially(text)
        else:
            editor.press("Backspace")
        editor.press("Enter")

    def change_quantity(self, row: int, quantity: Decimal) -> None:
        self.type_quantity(row, plain(quantity))

    def delete_row(self, position: int) -> None:
        """Deletes the grid row at the 1-based `position` with the row's delete button and answers Yes."""
        SaleBillPage(self.page).delete_grid_row(position)

    def expect_quantities(self, expected: list[Decimal]) -> None:
        """The filled rows show exactly these quantities, top to bottom (the empty last row is ignored)."""
        body = self.page.locator('[ref="eBodyContainer"]').first
        filled = body.locator(f'[col-id="{QUANTITY}"]').filter(has_text=re.compile(r"\d"))
        if not expected:
            expect(filled).to_have_count(0, timeout=GROSS_TIMEOUT_MS)
            return
        expect(filled).to_have_text([whole_number_text(each) for each in expected], timeout=GROSS_TIMEOUT_MS)

    def expect_gross(self, expected: Decimal) -> None:
        """The grid's totals row (sum of the line amounts) shows `expected`, to any number of decimals."""
        total = self.document.grid.totals_amount()
        expect(total).to_have_text(whole_number_text(expected), timeout=GROSS_TIMEOUT_MS)

    def expect_quantity_shown(self, row: int, quantity: Decimal) -> None:
        cell = self.document.grid.cell(row, QUANTITY)
        expect(cell).to_have_text(whole_number_text(quantity))

    def expect_quantity_not_shown(self, row: int, quantity: Decimal) -> None:
        cell = self.document.grid.cell(row, QUANTITY)
        expect(cell).not_to_have_text(whole_number_text(quantity))

    def double_save(self) -> None:
        """End twice with no wait between: a second press while the first save is under way."""
        self.document.save()
        self.page.keyboard.press("End")

    def close_with_escape_button(self) -> None:
        """The bill's Close (Esc) button; the bill asks before it discards what was typed."""
        self.page.locator(BILL_CLOSE_BUTTON).first.click()

    def accept_low_rate_if_asked(self) -> None:
        """A rate under the master's asks for confirmation (`DocumentItemGrid.confirm_low_price`)."""
        Confirmation(self.page).answer_yes_if_asked()

    def reopen(self, number: str) -> None:
        """Opens the saved bill from the sale bill list for change."""
        DocumentList(self.page, SaleBillDocument.menu).open_for_change(number)

    def save_changes(self) -> None:
        """Saves a bill opened for change, the way a new bill is saved."""
        self.save_and_confirm()

    def save_and_preview(self) -> bytes:
        """Saves, then previews in the Print window before it is closed; returns the PDF the server built.

        Preview posts the bill to `PrintTemplate/PrintTemplateExport` and opens the PDF in a new tab
        (trxnprint.component.ts:322-386); nothing goes to a printer."""
        self.document.save()
        self.document.confirm_save_window()
        self.document.screen.wait_for_loader()
        preview = self.page.locator("#billDetailForm").get_by_role("button", name=PREVIEW)
        expect(preview).to_be_visible(timeout=PROMPT_TIMEOUT_MS)
        with self.page.expect_response(BILL_PDF, timeout=PREVIEW_TIMEOUT_MS) as response:
            preview.click()
        pdf = response.value.body()
        self.document.leave_to_list()
        return pdf

    @property
    def last_deal_table(self) -> Locator:
        """The earlier deals of the selected item (itemLastDealsDetail.component.html), headed by S.Rate."""
        return self.page.get_by_role("table").filter(has_text=LAST_DEAL_RATE_HEADER)

    def expect_last_deal_lists(self, bill_number: str) -> None:
        expect(self.last_deal_table.get_by_role("cell", name=bill_number, exact=True)).to_be_visible(
            timeout=PROMPT_TIMEOUT_MS
        )

    def expect_discard_prompt(self) -> None:
        """After Close (Esc) with typed data the bill asks whether to leave without saving."""
        expect(self.page.locator("#btnYes")).to_be_visible(timeout=PROMPT_TIMEOUT_MS)

    def confirm_discard(self) -> None:
        self.page.locator("#btnYes").click()

    def expect_closed(self) -> None:
        expect(self.page.locator(BILL_CLOSE_BUTTON)).to_have_count(0, timeout=PROMPT_TIMEOUT_MS)

    def save(self) -> None:
        """Presses End until the save starts; nothing is confirmed."""
        self.document.save()

    def try_save(self) -> None:
        """Clicks the footer Save button; for a save the bill is expected to refuse or question."""
        # Why an id prefix: the footer button's id carries the window number (btnSave88).
        self.page.locator(FOOTER_SAVE_BUTTON).locator("visible=true").first.click()

    def save_and_confirm(self) -> None:
        self.document.save()
        self.document.expect_saved()

    @property
    def party_field(self) -> Locator:
        return self.document.header.field("Party Name")

    @property
    def patient_mobile_field(self) -> Locator:
        # Why an id prefix: the input's id ends in a per-tab number (txtptmobile88).
        return self.page.locator("[id^=txtptmobile]").locator("visible=true").first

    @property
    def sale_type_field(self) -> Locator:
        # Why an id prefix: as above (txtSaleType88); processout.transaction.component.html:382.
        return self.page.locator("[id^=txtSaleType]")

    @property
    def bill_number_field(self) -> Locator:
        # Why an id prefix: as above (txtentryNo88); typed into only when "Ask Bill No." is Yes.
        return self.page.locator("[id^=txtentryNo]").locator("visible=true").first

    def is_open(self) -> bool:
        return self.page.locator(BILL_CLOSE_BUTTON).first.is_visible()

    def leave_without_saving(self) -> None:
        self._totals.leave_without_saving()
