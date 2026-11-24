"""Receipt and payment vouchers made through a bank ledger by cheque (Accounting Trans. > Receipt/Payment)."""

import re
from datetime import date

from playwright.sync_api import Locator

from pages.accounting.entry_date import format_for_app
from pages.accounting.payment_page import PaymentPage
from pages.accounting.receipt_page import ReceiptPage
from pages.accounting.receipt_payment_voucher import ENTRY_ROW, ReceiptPaymentVoucher
from pages.accounting.toasts import Toasts
from pages.banking.yes_no_alert import YesNoAlert
from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from pages.reports.ledger_report_page import LedgerReportPage
from test_data.banking import BankEntry, SavedVoucher, VoucherKind

NO_SHORT_AMOUNT = "0"
DELETED = re.compile(r"voucher record deleted successfully", re.IGNORECASE)
CHEQUE_BOOK_PROMPT_MS = 3_000
DELETE_PROMPT_MS = 3_000
REFUSAL_TIMEOUT_MS = 15_000
SCREENS: dict[VoucherKind, type[ReceiptPaymentVoucher]] = {
    VoucherKind.PAYMENT: PaymentPage,
    VoucherKind.RECEIPT: ReceiptPage,
}


class BankVoucher(BasePage):
    def record(self, entry: BankEntry, bank: str) -> None:
        """Saves the voucher. The number shown before saving is provisional: under parallel saves the
        app stores a different one, so callers read the saved number from the ledger report."""
        screen = SCREENS[entry.kind](self.page)
        # A fresh dashboard first: after a save the sidebar group can be left collapsed and hidden.
        DashboardPage(self.page).open()
        screen.open_new_voucher()
        screen.choose_mode(bank)
        screen.select_account(ENTRY_ROW, entry.account)
        screen.enter_amount(entry.typed_amount)
        self._enter_cheque_number(entry.cheque_number)
        screen.enter_short_amount(NO_SHORT_AMOUNT)
        screen.save()
        screen.expect_saved()

    def delete(self, voucher: SavedVoucher) -> None:
        self._open_saved(voucher)
        self._press_delete()
        YesNoAlert(self.page).answer_yes()
        Toasts(self.page).expect_success_saying(DELETED)

    def expect_delete_refused_as_reconciled(self, voucher: SavedVoucher, cleared_on: date) -> None:
        """The refusal came straight after Delete in one run and after confirming Yes in another."""
        self._open_saved(voucher)
        self._press_delete()
        alert = YesNoAlert(self.page)
        if alert.is_shown(DELETE_PROMPT_MS):
            alert.answer_yes()
        refusal_text = f"Voucher Already Reconcile Of Date {format_for_app(cleared_on)}"
        refusal = re.compile(re.escape(refusal_text), re.IGNORECASE)
        Toasts(self.page).expect_any_saying(refusal, REFUSAL_TIMEOUT_MS)

    def _enter_cheque_number(self, cheque_number: str) -> None:
        self._grid_cell("insno").dblclick()
        editor = self.page.locator(f"#txt-insno-{ENTRY_ROW}")
        editor.press_sequentially(cheque_number)
        editor.press("Enter")
        self._decline_cheque_book()

    def _decline_cheque_book(self) -> None:
        """A payment by an unknown cheque asks "Do you want to create cheque book ?"; the test needs none."""
        alert = YesNoAlert(self.page)
        if alert.is_shown(CHEQUE_BOOK_PROMPT_MS):
            alert.answer_no()

    def _grid_cell(self, column: str) -> Locator:
        # Why CSS: ag-Grid exposes only row-id and col-id (same as pages/accounting/voucher_grid.py).
        body = self.page.locator('[ref="eBodyContainer"]').first
        return body.locator(f'[row-id="{ENTRY_ROW}"] [col-id="{column}"]')

    def _open_saved(self, voucher: SavedVoucher) -> None:
        """Opens the voucher from its account's ledger report: the number alone may not be unique, and
        the Payment and Receipt lists did not show today's bank vouchers on the QA tenant."""
        LedgerReportPage(self.page).open_voucher(voucher.account, voucher.number)

    def _press_delete(self) -> None:
        # The open voucher has one "Del Delete" button in its footer.
        self.page.get_by_role("button", name=re.compile(r"Delete$")).last.click()
