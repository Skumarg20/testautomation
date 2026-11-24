"""What every accounting voucher screen has in common: open, pick accounts, narrate, save, delete."""

import re
from datetime import date
from typing import ClassVar

from playwright.sync_api import Locator, Page, expect

from pages.accounting.accounting_menu import AccountingMenu, Screen
from pages.accounting.confirmation import Confirmation
from pages.accounting.entry_date import format_for_app
from pages.accounting.ledger_balances import LedgerBalances
from pages.accounting.ledger_picker import LedgerPicker
from pages.accounting.list_screen import ListScreen
from pages.accounting.loader import Loader
from pages.accounting.toasts import Toasts
from pages.accounting.voucher_grid import CellRef, VoucherGrid
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog

SAVE_SHORTCUT = "End"
DELETE_SHORTCUT = "Delete"
PREFERENCES_LOOKUP_MS = 2_000
UNSAVED_PROMPT_LOOKUP_MS = 1_000
SAVE_CONFIRM_LOOKUP_MS = 1_000
WARNING_LOOKUP_MS = 500
DATE_WARNING_LOOKUP_MS = 500
PRINT_WINDOW_LOOKUP_MS = 3_000
PICKER_LOOKUP_MS = 3_000
OWNER_CHECK_TIMEOUT_MS = 15_000
SAVE_BUTTON_NAME = re.compile(r"^save$", re.IGNORECASE)


class UnverifiedDeleteError(AssertionError):
    def __init__(self, voucher_number: str) -> None:
        super().__init__(
            f"Voucher {voucher_number} was not deleted: the case names no account, so nothing shows that "
            "the voucher is this test's own."
        )


class VoucherScreen(BasePage):
    SCREEN: ClassVar[Screen]

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.grid = VoucherGrid(page)
        self.toasts = Toasts(page)
        self.loader = Loader(page)
        self.ledgers = LedgerBalances(page)
        self._picker = LedgerPicker(page)
        self._confirmation = Confirmation(page)

    def open_new_voucher(self) -> None:
        AccountingMenu(self.page).open_screen(self.SCREEN)
        self.page.get_by_role("button", name="Create/F2", exact=True).click()
        self.loader.wait_until_idle()
        self._accept_transaction_preferences()

    def select_account(self, row: int, account: str) -> None:
        self._picker.choose(row, account)

    def ledgers_window_is_open(self) -> bool:
        return self._picker.window.is_visible()

    def close_ledgers_window(self) -> None:
        self._picker.close_window()

    def account_warning_shown(self) -> bool:
        return self.toasts.warning_appears(WARNING_LOOKUP_MS)

    def enter_narration(self, text: str) -> None:
        box = self.page.get_by_label("Narration").or_(self.page.locator("textarea")).first
        box.press("Control+A")
        box.press_sequentially(text)

    def expect_date_warning(self) -> None:
        """A date outside the open period raises a warning once focus moves to the account cell."""
        account_cell = self.grid.cell(CellRef(0, "ledgerLinkID"))
        account_cell.click()
        if not self.toasts.warning_appears(DATE_WARNING_LOOKUP_MS):
            account_cell.click()
        self.toasts.expect_warning_stays_visible()

    def save(self) -> None:
        self.page.keyboard.press(SAVE_SHORTCUT)

    def expect_saved(self) -> None:
        if appears_within(self._frame, SAVE_CONFIRM_LOOKUP_MS):
            self._save_button.click()
        self.toasts.expect_success()
        self.loader.wait_until_idle()
        self.return_to_list()

    def expect_rejected(self) -> None:
        self.toasts.expect_warning()
        self.return_to_list()

    def return_to_list(self) -> None:
        """Closes whatever the save left open: print preview, unsaved prompts, a ledger popup."""
        print_window = self.page.locator("#billDetailForm")
        if appears_within(print_window, PRINT_WINDOW_LOOKUP_MS):
            self._print_window_close.click()
        self._confirmation.answer_yes_if_asked()
        if appears_within(self._picker.window, PICKER_LOOKUP_MS):
            self._picker.close_window()
        self._confirmation.answer_yes_if_asked()

    def delete_voucher(self, voucher_number: str, accounts: tuple[str, ...]) -> None:
        """Deletes the voucher listed under `voucher_number` once it shows to book every one of `accounts`.
        A number read before saving is provisional (OA-010): under parallel saves it can belong to another
        test's voucher, which must not be deleted. The check narrows that race but cannot close it: another
        voucher that books the same ledgers (for example two shared ledgers such as Cash Account) passes."""
        if not accounts:
            raise UnverifiedDeleteError(voucher_number)
        AccountingMenu(self.page).open_screen(self.SCREEN)
        vouchers = ListScreen(self.page)
        vouchers.filter_to_this_week()
        vouchers.search(voucher_number)
        vouchers.open_only_row(voucher_number)
        self._expect_books_all_of(accounts)
        self.page.keyboard.press(DELETE_SHORTCUT)
        ConfirmDialog(self.page).answer_yes()
        self.toasts.expect_success()
        self.loader.wait_until_idle()

    def _expect_books_all_of(self, accounts: tuple[str, ...]) -> None:
        # Why CSS: ag-Grid exposes only col-id; the open voucher's account column is "ledgerLinkID".
        account_cells = self.page.locator('[ref="eBodyContainer"] [col-id="ledgerLinkID"]')
        for account in accounts:
            # Anchored, so "Cash" does not pass on a "Petty Cash" row.
            exact_name = re.compile(rf"^\s*{re.escape(account)}\s*$")
            expect(account_cells.filter(has_text=exact_name).first).to_be_visible(
                timeout=OWNER_CHECK_TIMEOUT_MS
            )

    def _field_input(self, label: str) -> Locator:
        # Why XPath: the label and its input share a wrapper but are not linked by for/id.
        wrapper = self.page.locator("label", has_text=label).locator(
            "xpath=ancestor::*[self::div or self::span][1]"
        )
        return wrapper.locator("input").first

    def _type_date(self, field: Locator, day: date) -> None:
        field.press("Control+A")
        field.press_sequentially(format_for_app(day))
        field.press("Enter")

    def _accept_transaction_preferences(self) -> None:
        self._dismiss_unsaved_prompt()
        if appears_within(self._frame, PREFERENCES_LOOKUP_MS):
            self._save_button.click()
            self.loader.wait_until_idle()
        self._dismiss_unsaved_prompt()

    def _dismiss_unsaved_prompt(self) -> None:
        prompt = self.page.locator("ngb-modal-window:not([aria-hidden='true']) unsave-bill .modal-header")
        close = self.page.locator("ngb-modal-window:not([aria-hidden='true'])").get_by_role(
            "button", name="×"
        )
        if appears_within(close, UNSAVED_PROMPT_LOOKUP_MS) and appears_within(
            prompt, UNSAVED_PROMPT_LOOKUP_MS
        ):
            close.first.click()

    @property
    def _frame(self) -> Locator:
        # Why CSS: the preferences and save-confirm window is a div with a class only.
        return self.page.locator("div.frameModal")

    @property
    def _save_button(self) -> Locator:
        return self.page.get_by_role("button", name=SAVE_BUTTON_NAME).first

    @property
    def _print_window_close(self) -> Locator:
        header = self.page.locator("div.modal-header.p-2")
        return header.get_by_text("×", exact=True).first
