"""Accounting Trans. > Debit Note: the "Debit Note Voucher List" and the values of one of its rows."""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.list_screen import ListScreen
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.components.app_texts import NO_BREAK_SPACE
from pages.inventory.item_alert import ItemAlert
from test_data.money import parse_amount

ROW_TIMEOUT_MS = 20_000
# The address carries the voucher type id of Debit Note on the QA company (seen live 2026-10-08).
LIST_PATH = "/transaction/voucher/debitnote/56"
LIST_HEADING = "Debit Note Voucher List"
VOUCHER_NUMBER = "voucherNo"
PARTY = "tmp_ledgername"
AMOUNT = "tmp_amount"
DATE = "entryDate"


class DebitNoteList(BasePage):
    def open(self) -> None:
        """By address: after a save the sidebar group can be half-collapsed and the menu click fails."""
        self.goto(LIST_PATH)
        expect(self.page.get_by_text(LIST_HEADING)).to_be_visible(timeout=ROW_TIMEOUT_MS)

    def find(self, voucher_number: str) -> None:
        self.open()
        vouchers = ListScreen(self.page)
        vouchers.filter_to_this_week()
        vouchers.search(voucher_number)

    def delete(self, voucher_number: str) -> None:
        """Opens the voucher from the list, deletes it with the Delete key and confirms."""
        self.find(voucher_number)
        ListScreen(self.page).open_row(voucher_number)
        self.page.keyboard.press("Delete")
        alert = ItemAlert(self.page)
        if alert.is_asked():
            # Why an id: the confirmation buttons carry aria-label "Close", not their visible Yes/No.
            alert.question.locator("#btnYes").click()
        Toasts(self.page).expect_success()

    def is_listed(self, voucher_number: str) -> bool:
        return self._row(voucher_number).count() > 0

    def expect_listed(self, voucher_number: str) -> None:
        expect(self._row(voucher_number)).to_have_count(1, timeout=ROW_TIMEOUT_MS)

    def expect_not_listed(self, voucher_number: str) -> None:
        expect(self._row(voucher_number)).to_have_count(0, timeout=ROW_TIMEOUT_MS)

    def party(self, voucher_number: str) -> str:
        return self._cell(voucher_number, PARTY).inner_text().replace(NO_BREAK_SPACE, " ").strip()

    def amount(self, voucher_number: str) -> Decimal:
        return parse_amount(self._cell(voucher_number, AMOUNT).inner_text())

    def date_text(self, voucher_number: str) -> str:
        return self._cell(voucher_number, DATE).inner_text().replace(NO_BREAK_SPACE, " ").strip()

    def _cell(self, voucher_number: str, column: str) -> Locator:
        return self._row(voucher_number).locator(f'[col-id="{column}"]')

    def _row(self, voucher_number: str) -> Locator:
        # Why col-id: the list is an ag-Grid; the voucher number cell is told apart only by its col-id.
        number_column = self.page.locator(f'[col-id="{VOUCHER_NUMBER}"]')
        number_cell = number_column.get_by_text(voucher_number, exact=True)
        return self.page.get_by_role("row").filter(has=number_cell)
