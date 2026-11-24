"""Accounting Trans. > Contra used as a cash transfer: cash paid into a bank (Cr cash, Dr bank).

Builds on the shared contra screen (pages/accounting). What it adds: the bank row's instrument number,
the "create cheque book?" question that follows it, and finding, changing and deleting the voucher by
its cash ledger, which is unique to the test (the voucher number is a tenant-wide series).
"""

import re
from datetime import date
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.contra_page import ContraPage
from pages.accounting.list_screen import ListScreen
from pages.accounting.voucher_cases import Leg
from pages.accounting.voucher_grid import CellRef
from pages.accounting.waiting import appears_within
from pages.banking.grid_rows import GridRows
from pages.components.confirm_dialog import ConfirmDialog
from pages.dashboard_page import DashboardPage
from test_data.cash_transfer import CashDeposit

CASH_ROW = 0
BANK_ROW = 1
CHEQUE_BOOK_QUESTION = "create cheque book"
CHEQUE_BOOK_LOOKUP_MS = 3_000
EDITOR_LOOKUP_MS = 2_000
MODIFY_BUTTON = "Modify"
ROW_TIMEOUT_MS = 30_000
DELETE_SHORTCUT = "Delete"


class ContraTransfer(ContraPage):
    def record(self, deposit: CashDeposit) -> None:
        """Enters and saves the deposit; fails if the app does not confirm the save."""
        self.enter(deposit)
        self.save()
        self.expect_saved()

    def enter(self, deposit: CashDeposit) -> None:
        self.start_new()
        self.enter_cash_leg(deposit)
        self.enter_bank_leg(deposit)
        self.enter_narration(f"QA cash deposit into {deposit.bank_ledger}")

    def start_new(self) -> None:
        DashboardPage(self.page).open()
        self.open_new_voucher()
        self.enter_date(date.today())

    def enter_cash_leg(self, deposit: CashDeposit) -> None:
        self.choose_side(CASH_ROW, "credit")
        self.select_account(CASH_ROW, deposit.cash_ledger)
        self.enter_leg_amount(CASH_ROW, Leg("credit", deposit.cash_ledger, deposit.typed_amount))

    def enter_bank_leg(self, deposit: CashDeposit) -> None:
        self.enter_bank_leg_without_cheque(deposit)
        self.enter_cheque_number(deposit.cheque_number)

    def enter_bank_leg_without_cheque(self, deposit: CashDeposit) -> None:
        self.choose_side(BANK_ROW, "debit")
        self.select_account(BANK_ROW, deposit.bank_ledger)
        self.enter_leg_amount(BANK_ROW, Leg("debit", deposit.bank_ledger, deposit.typed_amount))

    def enter_cheque_number(self, cheque_number: str) -> None:
        field = self._cheque_number_input(BANK_ROW)
        if not appears_within(field, CHEQUE_BOOK_LOOKUP_MS):
            self._cheque_number_cell(BANK_ROW).click()
        field.press("Control+A")
        field.press_sequentially(cheque_number)
        field.press("Enter")
        self._decline_cheque_book()

    def expect_save_refused_saying(self, message: str) -> None:
        self.toasts.expect_any_saying(_case_insensitive(message))

    def change_amount(self, deposit: CashDeposit, amount: Decimal) -> None:
        """Opens the saved deposit, puts the new amount on both rows and saves the change."""
        self._open_saved(deposit)
        self.page.get_by_role("button", name=MODIFY_BUTTON).click()
        self.loader.wait_until_idle()
        changed = deposit.with_amount(amount)
        self._retype_amount(CellRef(CASH_ROW, "crAmount"), changed.typed_amount)
        self._retype_amount(CellRef(BANK_ROW, "drAmount"), changed.typed_amount)
        self.save()
        self.expect_saved()

    def delete(self, deposit: CashDeposit) -> None:
        self._open_saved(deposit)
        self.page.keyboard.press(DELETE_SHORTCUT)
        ConfirmDialog(self.page).answer_yes()
        # The success toast is short-lived and was missed under load (2026-10-16): the list is the proof.
        self.loader.wait_until_idle()
        self._open_list(deposit)
        expect(self._party_cell(deposit)).to_have_count(0, timeout=ROW_TIMEOUT_MS)

    def listed_row(self, deposit: CashDeposit) -> dict[str, str]:
        """Today's list row whose Party Name (the first, credit ledger) is the deposit's cash ledger,
        as column header -> cell text."""
        self._open_list(deposit)
        row = self._list_row(deposit)
        expect(row.get_by_role("gridcell").first).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return GridRows(self.page).read_by_header(row)

    def _open_saved(self, deposit: CashDeposit) -> None:
        self._open_list(deposit)
        # The party cell, not the first one: the expanded sidebar covers the Date column.
        self._party_cell(deposit).dblclick()
        self.loader.wait_until_idle()

    def _open_list(self, deposit: CashDeposit) -> None:
        DashboardPage(self.page).open()
        AccountingMenu(self.page).open_screen(self.SCREEN)
        ListScreen(self.page).search(deposit.cash_ledger)

    def _list_row(self, deposit: CashDeposit) -> Locator:
        row = self.page.get_by_role("row").filter(has=self._party_cell(deposit))
        expect(row).to_have_count(1, timeout=ROW_TIMEOUT_MS)
        return row

    def _party_cell(self, deposit: CashDeposit) -> Locator:
        return self.page.get_by_role("gridcell", name=deposit.cash_ledger, exact=True)

    def _retype_amount(self, ref: CellRef, amount: str) -> None:
        editor = self.grid.cell_input(ref)
        if not appears_within(editor, EDITOR_LOOKUP_MS):
            self.grid.cell(ref).click()
        editor.press("Control+A")
        editor.press_sequentially(amount)
        editor.press("Enter")

    def _decline_cheque_book(self) -> None:
        question = self.page.get_by_role("dialog").filter(has_text=CHEQUE_BOOK_QUESTION)
        if appears_within(question, CHEQUE_BOOK_LOOKUP_MS):
            # Why an id: Yes and No both carry aria-label="Close" (see pages/accounting/confirmation.py).
            question.locator("#btnNo").click()
            expect(question).to_be_hidden()

    def _cheque_number_cell(self, row: int) -> Locator:
        # Why CSS: ag-Grid exposes only row-id and col-id (the shared VoucherGrid has no "insno" column).
        body = self.page.locator('[ref="eBodyContainer"]').first
        return body.locator(f'[row-id="{row}"] [col-id="insno"]')

    def _cheque_number_input(self, row: int) -> Locator:
        # Why an id: the Inst. No editor is a bare input whose id carries the row index.
        return self.page.locator(f"#txt-insno-{row}")


def _case_insensitive(message: str) -> re.Pattern[str]:
    return re.compile(re.escape(message), re.IGNORECASE)
