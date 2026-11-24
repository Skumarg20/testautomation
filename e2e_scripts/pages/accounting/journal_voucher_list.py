"""Accounting Trans. > Journal list: finds today's journal voucher of a ledger and deletes it."""

from playwright.sync_api import expect

from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.list_screen import ListScreen
from pages.accounting.loader import Loader
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog

DELETE_SHORTCUT = "Delete"
ROW_TIMEOUT_MS = 30_000


class JournalVoucherList(BasePage):
    def delete_voucher_of(self, ledger_name: str) -> None:
        """The list shows today's vouchers by default; the ledger is unique to the test, so is its voucher."""
        AccountingMenu(self.page).open_screen("Journal")
        vouchers = ListScreen(self.page)
        vouchers.search(ledger_name)
        expect(self.page.get_by_role("gridcell", name=ledger_name, exact=True)).to_have_count(
            1, timeout=ROW_TIMEOUT_MS
        )
        vouchers.open_row(ledger_name)
        self.page.keyboard.press(DELETE_SHORTCUT)
        ConfirmDialog(self.page).answer_yes()
        Toasts(self.page).expect_success()
        Loader(self.page).wait_until_idle()
