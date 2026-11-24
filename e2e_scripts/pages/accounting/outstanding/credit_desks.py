"""Receipts and sale returns for the outstanding cases: saved, changed, re-adjusted and deleted.

Receipt (live 2026-10-09): Accounting Trans. > Receipt > Create/F2, mode Cash Account, party, date, amount;
Enter on Short Amount opens Bill Adjustment; F10 closes it; End saves ("Receipt Voucher Saved
Successfully !") and leaves an empty receipt open for the next one.
"""

from datetime import date
from decimal import Decimal

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, expect

from pages.accounting.accounting_menu import AccountingMenu
from pages.accounting.bill_adjustment import BillAdjustmentWindow
from pages.accounting.list_screen import ListScreen
from pages.accounting.outstanding.document_desk import DocumentDesk, UnexpectedNewDocumentsError
from pages.accounting.outstanding.scenario import BillAllocations
from pages.accounting.receipt_page import ReceiptPage
from pages.accounting.voucher_grid import CellRef, Column
from pages.dashboard_page import DashboardPage
from pages.reports.ledger_report_page import LedgerReportPage
from pages.sale.documents.mode_of_payment import ModeOfPayment
from pages.sale.documents.returns import MANUAL_RETURN, SaleReturn
from test_data.banking import VoucherKind

CASH_MODE = "Cash Account"
ENTRY_ROW = 0
WINDOW_LOOKUP_MS = 8_000
REFUND_LOOKUP_MS = 10_000
EDITOR_TIMEOUT_MS = 15_000
MODIFY_SHORTCUT = "F3"
PARTY_AMOUNT: Column = "crAmount"
CASH_AMOUNT: Column = "drAmount"
CASH_LINE = 1


class ReceiptDesk:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._receipt = ReceiptPage(page)
        self._adjustment = BillAdjustmentWindow(page)
        self._known_numbers: set[str] = set()
        self._parties: dict[str, str] = {}

    def create(self, party: str, amount: Decimal, allocations: BillAllocations) -> str:
        self._start_for(party)
        self._receipt.enter_row_date(date.today())
        self._receipt.enter_amount(format(amount, "f"))
        self._adjust_from_short_amount(allocations)
        self._save()
        return self._saved_number(party)

    def change(self, number: str, amount: Decimal, allocations: BillAllocations) -> None:
        """Modify shows the receipt as two lines, Cr party and Dr cash (live 2026-10-12): both amounts
        change. An advance receipt does not open Bill Adjustment on Enter (OA-066), so it is opened when
        bills must be allocated."""
        self._open_for_change(number)
        self._type_party_amount(amount)
        if self._adjustment.is_open(WINDOW_LOOKUP_MS):
            self._allocate(allocations)
        elif allocations:
            self._open_adjustment_from_amount()
            self._allocate(allocations)
        self._type_line_amount(CASH_LINE, CASH_AMOUNT, amount)
        self._save()

    def readjust(self, number: str, allocations: BillAllocations) -> None:
        self._open_for_change(number)
        self._open_adjustment_from_amount()
        self._allocate(allocations)
        self._save()

    def expect_over_adjustment_refused(self, number: str, bill_number: str, amount: Decimal) -> None:
        self._open_for_change(number)
        self._open_adjustment_from_amount()
        self._adjustment.show_bills()
        self._adjustment.unselect_all()
        self._adjustment.expect_over_bill_value_refused(bill_number, amount)
        self._adjustment.close()
        self._receipt.return_to_list()

    def delete(self, number: str) -> None:
        DashboardPage(self._page).open()
        self._receipt.delete_voucher(number, (self._parties[number],))

    def _saved_number(self, party: str) -> str:
        """The number of the receipt just saved, read from the party's ledger report: the party is new to
        the test, so every receipt there is ours. The number shown before saving can be taken by another
        save in between (OA-010)."""
        listed = LedgerReportPage(self._page).voucher_numbers(party, VoucherKind.RECEIPT.value)
        new_numbers = set(listed) - self._known_numbers
        if len(new_numbers) != 1:
            raise UnexpectedNewDocumentsError(party, sorted(new_numbers))
        number = new_numbers.pop()
        self._known_numbers.add(number)
        self._parties[number] = party
        return number

    def _start_for(self, party: str) -> None:
        """A ledger saved seconds earlier is sometimes missing from the account picker (OA-007,
        2026-10-10), as in Select Party on sale documents; the unsaved voucher is left and started again."""
        try:
            self._open_new_for(party)
        except (AssertionError, PlaywrightError):
            if self._receipt.ledgers_window_is_open():
                self._receipt.close_ledgers_window()
            self._receipt.return_to_list()
            self._open_new_for(party)

    def _open_new_for(self, party: str) -> None:
        DashboardPage(self._page).open()
        self._receipt.open_new_voucher()
        self._receipt.choose_mode(CASH_MODE)
        self._receipt.select_account(ENTRY_ROW, party)

    def _open_for_change(self, number: str) -> None:
        """A receipt opens read-only ("Modify Receipt Voucher": Cr party, Dr cash); F3 makes it editable."""
        DashboardPage(self._page).open()
        AccountingMenu(self._page).open_screen(ReceiptPage.SCREEN)
        vouchers = ListScreen(self._page)
        vouchers.filter_to_this_week()
        vouchers.search(number)
        vouchers.open_row(number)
        self._page.keyboard.press(MODIFY_SHORTCUT)
        self._receipt.loader.wait_until_idle()

    def _type_party_amount(self, amount: Decimal) -> None:
        """Enter in the party's Credit editor (`#txt-crAmount-0`) opens Bill Adjustment (live 2026-10-09)."""
        self._type_line_amount(ENTRY_ROW, PARTY_AMOUNT, amount)

    def _type_line_amount(self, row: int, column: Column, amount: Decimal) -> None:
        editor = self._line_amount_editor(row, column)
        editor.press("Control+A")
        editor.press_sequentially(format(amount, "f"))
        editor.press("Enter")

    def _adjust_from_short_amount(self, allocations: BillAllocations) -> None:
        """Focus is on Short Amount after the amount; Enter there opens the window (bill-by-bill party)."""
        self._page.keyboard.press("Enter")
        if self._adjustment.is_open(WINDOW_LOOKUP_MS):
            self._allocate(allocations)

    def _open_adjustment_from_amount(self) -> None:
        self._party_amount_editor().press("Enter")
        self._adjustment.expect_open()

    def _party_amount_editor(self) -> Locator:
        return self._line_amount_editor(ENTRY_ROW, PARTY_AMOUNT)

    def _line_amount_editor(self, row: int, column: Column) -> Locator:
        self._receipt.grid.cell(CellRef(row, column)).click()
        # Why an id: the editor is an ag-Grid popup outside the cell; the app names it by column and row.
        editor = self._page.locator(f"#txt-{column}-{row}")
        expect(editor).to_be_visible(timeout=EDITOR_TIMEOUT_MS)
        return editor

    def _allocate(self, allocations: BillAllocations) -> None:
        self._adjustment.allocate(allocations)
        self._adjustment.save()

    def _save(self) -> None:
        self._receipt.save()
        self._receipt.toasts.expect_success()
        self._receipt.loader.wait_until_idle()


class SaleReturnDesk(DocumentDesk):
    """Sale > Return as a manual return of the 0% item, saved with no refund in its Mode Of Payment window.

    The Bill Adjustment window opens after the save only when Tab was pressed on the grid's first empty
    row (`isTabkeypressingrid`, processout.transaction.component.ts:7299 and :12062); without it the return
    stayed unadjusted (OA-016, 2026-10-12). So every save leaves the grid with Tab first.
    """

    def __init__(self, page: Page, item: str) -> None:
        self._return = SaleReturn(page)
        super().__init__(page, item, self._return)
        self._refund = ModeOfPayment(page)

    def create(self, party: str, amount: Decimal, allocations: BillAllocations) -> str:
        self._start_for(party)
        self._line.add(amount)
        self._save(allocations)
        return self._saved_number(party)

    def change(self, number: str, amount: Decimal, allocations: BillAllocations) -> None:
        self._open_for_change(number)
        self._reprice(amount)
        self._save(allocations)

    def readjust(self, number: str, allocations: BillAllocations) -> None:
        self._open_for_change(number)
        self._save(allocations)

    def expect_over_adjustment_refused(self, number: str, bill_number: str, amount: Decimal) -> None:
        self._open_for_change(number)
        self._save_without_refund()
        self._adjustment.expect_open()
        self._adjustment.show_bills()
        self._adjustment.unselect_all()
        self._adjustment.expect_over_bill_value_refused(bill_number, amount)
        self._adjustment.close()
        self._close_print_window()

    def _choose_party(self, party: str) -> None:
        self._return.choose_party_for_return(party, MANUAL_RETURN)

    def _save(self, allocations: BillAllocations) -> None:
        self._save_without_refund()
        self._settle_adjustment(allocations)
        self._close_print_window()

    def _save_without_refund(self) -> None:
        self._save_from_footer()
        if self._refund.is_open(REFUND_LOOKUP_MS):
            self._refund.save()
