"""Receipt and payment share one layout: Account, Date, Amount and Short Amount in a single grid row."""

from datetime import date
from typing import ClassVar

from playwright.sync_api import Locator, expect

from pages.accounting.entry_date import format_for_app
from pages.accounting.voucher_grid import CellRef
from pages.accounting.voucher_number_setting import VoucherNumberSetting
from pages.accounting.voucher_screen import VoucherScreen
from pages.accounting.waiting import appears_within

ENTRY_ROW = 0
FIELD_LOOKUP_MS = 1_000
NUMBER_LOOKUP_MS = 2_000
SELECTION_LOOKUP_MS = 2_000


class VoucherNumberHiddenError(AssertionError):
    def __init__(self) -> None:
        super().__init__(
            "The voucher shows no number: 'Voucher No. Required ?' is off. Call turn_on_voucher_numbers() "
            "while a voucher is open, then open a new voucher."
        )


class ReceiptPaymentVoucher(VoucherScreen):
    BALANCE_SIGN: ClassVar[int]
    """+1 when the account's balance grows by the voucher total (payment), -1 when it shrinks (receipt)."""

    def choose_mode(self, ledger: str) -> None:
        """Sets the Receipt / Payment Mode. The app remembers the last mode per login, so a bank voucher made
        by another test changes the default."""
        # The mode typeahead is the only "Search here.." box on a new voucher.
        mode = self.page.get_by_role("combobox", name="Search here..").first
        if mode.input_value() == ledger:
            return
        mode.click()
        mode.press("Control+A")
        mode.press_sequentially(ledger)
        self.page.get_by_role("listbox").get_by_role("option", name=ledger, exact=True).click()
        expect(mode).to_have_value(ledger)

    def enter_row_date(self, day: date) -> None:
        ref = CellRef(ENTRY_ROW, "entryDate")
        editor = self.grid.cell_input(ref)
        if not appears_within(editor, FIELD_LOOKUP_MS):
            self.grid.cell(ref).click()
        editor.press("Control+A")
        editor.press_sequentially(format_for_app(day))
        editor.press("Enter")

    def enter_amount(self, amount: str) -> None:
        self.grid.type_into(CellRef(ENTRY_ROW, "drAmount"), amount)

    def enter_short_amount(self, amount: str) -> None:
        ref = CellRef(ENTRY_ROW, "crAmount")
        if appears_within(self.grid.cell(ref), FIELD_LOOKUP_MS):
            self.grid.type_into(ref, amount)
        self._close_account_popup_if_opened()

    def turn_on_voucher_numbers(self) -> None:
        """Switches "Voucher No. Required ?" on for the whole tenant. Call it while a voucher is open: the
        Control Room shows the settings of the open document. A voucher opened afterwards shows its number.
        Callers must run in the "chemist-tenant" xdist group."""
        VoucherNumberSetting(self.page).require_voucher_numbers()

    def shows_voucher_number(self) -> bool:
        return appears_within(self._number_cell, NUMBER_LOOKUP_MS)

    def voucher_number(self) -> str:
        """The number shown in the grid of the open voucher; provisional until the voucher is saved."""
        if not self.shows_voucher_number():
            raise VoucherNumberHiddenError
        return self._number_cell.inner_text().strip()

    @property
    def _number_cell(self) -> Locator:
        return self.grid.cell(CellRef(ENTRY_ROW, "voucherNo"))

    def _close_account_popup_if_opened(self) -> None:
        window = self._picker.window
        if appears_within(window, SELECTION_LOOKUP_MS):
            self.page.keyboard.press("Escape")
        expect(window).to_be_hidden()
