"""Debit note, credit note, contra and journal share one layout: a header date and two account rows."""

from datetime import date

from playwright.sync_api import Locator, expect

from pages.accounting.voucher_cases import Leg, Side
from pages.accounting.voucher_grid import CellRef
from pages.accounting.voucher_screen import VoucherScreen
from pages.accounting.waiting import appears_within

DATE_LABEL = "Date"
VOUCHER_NUMBER_LABEL = "Voucher No."
SIDE_OPTION: dict[Side, str] = {"debit": "Dr", "credit": "Cr"}
SIDE_EDITOR_LOOKUP_MS = 2_000


class TwoSidedVoucher(VoucherScreen):
    def enter_date(self, day: date) -> None:
        self._type_date(self._date_input, day)

    def choose_side(self, row: int, side: Side) -> None:
        """A screen with a Cr./Dr. column (journal) starts each row as Dr; only that side's amount opens."""
        expect(self.grid.cell(CellRef(row, "ledgerLinkID"))).to_be_visible()
        cell = self.grid.cell(CellRef(row, "creditOrDebit"))
        if not cell.is_visible() or cell.inner_text().strip() == SIDE_OPTION[side]:
            return
        editor = cell.get_by_role("combobox")
        if not appears_within(editor, SIDE_EDITOR_LOOKUP_MS):
            cell.click()
        editor.select_option(label=SIDE_OPTION[side])

    def enter_leg_amount(self, row: int, leg: Leg) -> None:
        self.grid.type_into(CellRef(row, leg.column), leg.amount)

    def voucher_number(self) -> str:
        return self._field_input(VOUCHER_NUMBER_LABEL).input_value()

    @property
    def _date_input(self) -> Locator:
        return self._field_input(DATE_LABEL)
