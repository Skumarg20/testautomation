"""Report > Accounts Report: Trial Balance, Day Book and Trading, Profit and Loss Account.

Each report is an ag-Grid that renders only the rows in view, so a row is found by scrolling to it.
Amounts are read as Decimal; an empty amount cell means zero.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.loader import Loader
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.components.whole_text import whole_text
from test_data.money import parse_amount

REPORT_TIMEOUT_MS = 60_000
NAVIGATION_TIMEOUT_MS = 90_000
ROW_LOOKUP_MS = 700
SCROLL_STEP_PX = 500
SCROLL_ATTEMPTS = 40
STOCK_PROMPT_LOOKUP_MS = 10_000
EXPAND_ALL = re.compile(r"Expand All")
COLLAPSE_ALL = re.compile(r"Collapse All")


class ReportRowNotFoundError(LookupError):
    def __init__(self, report: str, text: str) -> None:
        super().__init__(f'{report}: no row named "{text}" after scrolling the whole grid')


@dataclass(frozen=True)
class DebitCredit:
    debit: Decimal
    credit: Decimal


@dataclass(frozen=True)
class DayBookEntry:
    voucher_no: str
    voucher_type: str
    amounts: DebitCredit


def _amount(cell: Locator) -> Decimal:
    text = cell.inner_text().strip()
    return parse_amount(text) if text else Decimal(0)


class AccountsReport(BasePage):
    PATH: str
    TITLE: re.Pattern[str]

    def open(self) -> None:
        self.goto(self.PATH, NAVIGATION_TIMEOUT_MS)
        Loader(self.page).wait_until_idle()
        self._before_report_shows()
        expect(self.page.get_by_role("heading", name=self.TITLE, level=1)).to_be_visible(
            timeout=REPORT_TIMEOUT_MS
        )
        expect(self._grid.get_by_role("columnheader").first).to_be_attached(timeout=REPORT_TIMEOUT_MS)

    def expand_all(self) -> None:
        """The report remembers its last expand state, so it may already be expanded."""
        expand = self.page.get_by_role("button", name=EXPAND_ALL)
        collapse = self.page.get_by_role("button", name=COLLAPSE_ALL)
        expect(expand.or_(collapse)).to_be_visible(timeout=REPORT_TIMEOUT_MS)
        if expand.is_visible():
            expand.click()
            Loader(self.page).wait_until_idle()
        expect(collapse).to_be_visible(timeout=REPORT_TIMEOUT_MS)

    def _before_report_shows(self) -> None:
        """Hook for a prompt the report raises before it renders; most reports have none."""

    def _scroll_to_row(self, row: Locator) -> Locator:
        self._grid.hover()
        for _ in range(SCROLL_ATTEMPTS):
            if appears_within(row, ROW_LOOKUP_MS):
                return row.first
            self.page.mouse.wheel(0, SCROLL_STEP_PX)
        raise ReportRowNotFoundError(self.PATH, str(row))

    def _row_with_text(self, text: str) -> Locator:
        """The row with a cell whose whole text is `text`."""
        name_cell = self.page.get_by_role("gridcell").filter(has_text=whole_text(text))
        return self._scroll_to_row(self.page.get_by_role("row").filter(has=name_cell))

    @property
    def _grid(self) -> Locator:
        return self.page.get_by_role("grid").first


class TrialBalancePage(AccountsReport):
    PATH = "/report/trialbalance/tb-group"
    TITLE = re.compile(r"^Trial Balance")
    DEBIT_COLUMN = 1
    CREDIT_COLUMN = 2

    def balance_of(self, name: str) -> DebitCredit:
        cells = self._row_with_text(name).get_by_role("gridcell")
        expect(cells.first).to_have_text(name, timeout=REPORT_TIMEOUT_MS)
        return DebitCredit(_amount(cells.nth(self.DEBIT_COLUMN)), _amount(cells.nth(self.CREDIT_COLUMN)))

    def grand_totals(self) -> DebitCredit:
        cells = self.page.get_by_role("row").filter(has_text="Grand Total").first.get_by_role("gridcell")
        expect(cells.nth(self.CREDIT_COLUMN)).not_to_have_text("", timeout=REPORT_TIMEOUT_MS)
        return DebitCredit(_amount(cells.nth(self.DEBIT_COLUMN)), _amount(cells.nth(self.CREDIT_COLUMN)))


class DayBookPage(AccountsReport):
    """Opens on today's date. One row per voucher line; columns are addressed by ag-Grid col-id."""

    PATH = "/report/daybook/db-default"
    TITLE = re.compile(r"^Day Book")

    def entry_of(self, ledger_name: str) -> DayBookEntry:
        row = self._row_with_text(ledger_name)
        # Why CSS: ag-Grid gives the cells no accessible column name, only a col-id.
        expect(row.locator('[col-id="Ledger"]')).to_have_text(ledger_name)
        amounts = DebitCredit(
            _amount(row.locator('[col-id="Debit"]')), _amount(row.locator('[col-id="Credit"]'))
        )
        return DayBookEntry(
            voucher_no=row.locator('[col-id="VoucherNo"]').inner_text().strip(),
            voucher_type=row.locator('[col-id="VoucherType"]').inner_text().strip(),
            amounts=amounts,
        )


class ProfitLossPage(AccountsReport):
    """Two-sided layout: expenses on the left (col-id "First"), incomes on the right ("Second")."""

    PATH = "/report/profitloss"
    TITLE = re.compile(r"^Trading, Profit and Loss Account")

    def expense_amount(self, ledger_name: str) -> Decimal:
        return self._side_amount(ledger_name, "First")

    def income_amount(self, ledger_name: str) -> Decimal:
        return self._side_amount(ledger_name, "Second")

    def _before_report_shows(self) -> None:
        """The report first asks "Update Balance Sheet Stock?"; "No" leaves the stock figures untouched."""
        prompt = self.page.get_by_role("dialog").filter(has_text="Stock Valuation")
        if appears_within(prompt, STOCK_PROMPT_LOOKUP_MS):
            prompt.get_by_role("button", name="No", exact=True).click()
            Loader(self.page).wait_until_idle()

    def _side_amount(self, ledger_name: str, side: str) -> Decimal:
        # Why CSS: ag-Grid col-ids are the only way to tell the expense side from the income side.
        name_cell = self.page.locator(f'[col-id="{side}"]').filter(has_text=whole_text(ledger_name))
        row = self._scroll_to_row(self.page.get_by_role("row").filter(has=name_cell))
        return _amount(row.locator(f'[col-id="{side}TotalAmount"]'))
