"""What the manufacturing vouchers show beyond a save: line rate and amount, the entry date check, the
party window, and opening a saved voucher for a change.

From the Angular source, unverified live:
- the date picker's input id starts with `txtbillDate` (processout.transaction.component.html:131,
  transactionin.component.html:127); a date outside the books year gives "Invalid entry date ! Date should be
  between financial year." (global.ts:19494, processout.transaction.component.ts:1832,
  transactionin.component.ts:2200);
- the party window of Material Issue lists only Sundry Creditor (Manufacturer) ledgers
  (`partyTypeFixedId`, billofmaterialissue.factory.ts:29);
- a saved voucher opens for change from the list row's edit icon; it may open read-only with "F3 Modify"
  (as pages/accounting/outstanding/document_list.py:31-45 saw live on the sale list).
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.manufacturing.menu import ManufacturingMenu, ManufacturingScreen
from pages.purchase.documents.document_list import DocumentList
from pages.purchase.documents.feedback import AppFeedback
from pages.stock.messages import StockMessages
from test_data.money import parse_amount

OUTSIDE_BOOKS_YEAR = re.compile(r"Invalid entry date ! Date should be between financial year\.")
MODIFY_LOOKUP_MS = 3_000
MODIFY_BUTTON = re.compile(r"^\s*F3\s*Modify")
CELL_TIMEOUT_MS = 20_000
BATCH_LOOKUP_MS = 5_000
WINDOW_TIMEOUT_MS = 20_000


class VoucherLines(BasePage):
    def rate(self, row: int) -> Decimal:
        return self._amount_in(row, "salePurchaseRate")

    def amount(self, row: int) -> Decimal:
        return self._amount_in(row, "DisplayAmount")

    def has_batch_column(self) -> bool:
        return appears_within(self._cell(0, "batchLinkID"), BATCH_LOOKUP_MS)

    def _amount_in(self, row: int, column: str) -> Decimal:
        cell = self._cell(row, column)
        expect(cell).to_be_visible(timeout=CELL_TIMEOUT_MS)
        return parse_amount(cell.inner_text().strip())

    def _cell(self, row: int, column: str) -> Locator:
        # Why CSS: the line grid is an ag-Grid (as EntryGrid); the first body container holds the lines.
        return self.page.locator(".ag-body-container").first.locator(f'[row-id="{row}"] [col-id="{column}"]')


class VoucherDate(BasePage):
    def enter(self, date_text: str) -> None:
        """Types a dd-MM-yyyy date into the voucher's date and confirms it with Enter."""
        # Why CSS: the date picker's label is not tied to it; its id carries a per-tab suffix.
        field = self.page.locator('input[id^="txtbillDate"]').first
        field.press("Control+A")
        field.press_sequentially(date_text)
        field.press("Enter")

    def expect_outside_books_year_refused(self) -> None:
        StockMessages(self.page).expect_shown(OUTSIDE_BOOKS_YEAR)


class PartyWindow(BasePage):
    def expect_offered(self, party: str) -> None:
        expect(self._cell(party).first).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def expect_not_offered(self, party: str) -> None:
        expect(self._cell(party)).to_have_count(0)

    def pick(self, party: str) -> None:
        """Clicks the party without expecting the window to close: the screen may refuse it."""
        self.search(party)
        self._cell(party).first.click()

    def search(self, text: str) -> None:
        AppFeedback(self.page).wait_for_loader()
        search = self._window.get_by_role("searchbox")
        search.press("Control+A")
        search.press_sequentially(text, delay=150)

    def _cell(self, party: str) -> Locator:
        exactly = re.compile(rf"^\s*{re.escape(party)}\s*$", re.IGNORECASE)
        return self._window.locator(".ag-cell-value").filter(has_text=exactly)

    @property
    def _window(self) -> Locator:
        # Why CSS: the party window is a Bootstrap modal with no title role (as SelectionWindow).
        return self.page.locator("div.modal-dialog.modal-lg")


def open_for_change(page: Page, screen: ManufacturingScreen, number: str) -> None:
    """Opens a saved voucher of `screen` for change (MF-26)."""
    ManufacturingMenu(page).open_screen(screen)
    vouchers = DocumentList(page)
    vouchers.filter_this_week()
    vouchers.find(number)
    # Why a class: the edit button is an icon with neither a title nor an accessible name.
    vouchers.row(number).locator("button.mksBtn.edit").click()
    AppFeedback(page).wait_for_loader()
    if appears_within(page.get_by_role("button", name=MODIFY_BUTTON), MODIFY_LOOKUP_MS):
        page.keyboard.press("F3")
        AppFeedback(page).wait_for_loader()
