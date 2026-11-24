"""One party's bill-wise outstanding, opened with F8 from Master > Ledger (the same view as Report >
Outstanding Report > Receivable > Ledger Wise). That receivable list leaves out a party whose net balance is
zero even when it has an open bill and an equal advance (OA-013, 2026-10-09), so it is not used.

For Sundry Debtors the report shows unadjusted credits (advances, unadjusted receipts and returns) as
negative rows (sp_OutstandingReportDetails, scenarios/outstanding-advance.md); there is no advance column.
So outstanding is the sum of the positive rows and advance is minus the sum of the negative rows.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, expect

from pages.accounting.loader import Loader
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from pages.masters.master_list import LedgerList
from test_data.money import parse_amount

BILL_NUMBER_HEADER = "Bill No"
OUTSTANDING_HEADER = "Outstanding"
GRAND_TOTAL = "Grand Total"
ANY_DIGIT = re.compile(r"\d")
SCREEN_TIMEOUT_MS = 60_000
MAX_SCROLL_STEPS = 8
HEADER_LOOKUP_MS = 1_000


@dataclass(frozen=True)
class OutstandingRow:
    bill_number: str
    outstanding: Decimal


@dataclass(frozen=True)
class PartyOutstanding:
    rows: tuple[OutstandingRow, ...]

    @property
    def outstanding(self) -> Decimal:
        return sum((row.outstanding for row in self.rows if row.outstanding > 0), Decimal(0))

    @property
    def advance(self) -> Decimal:
        return -sum((row.outstanding for row in self.rows if row.outstanding < 0), Decimal(0))

    def bill_balance(self, bill_number: str) -> Decimal:
        """A bill missing from the report is fully settled: the report drops zero-balance rows."""
        balances = [row.outstanding for row in self.rows if row.bill_number == bill_number]
        return balances[0] if balances else Decimal(0)


class OutstandingReport(BasePage):
    def read(self, party: str) -> PartyOutstanding:
        """A ledger saved minutes earlier can be missing from a list that was loaded before it (OA-014,
        2026-10-10); the list is opened once more in that case."""
        try:
            self._open_outstanding_of(party)
        except (AssertionError, PlaywrightError):
            self._open_outstanding_of(party)
        return PartyOutstanding(tuple(self._rows()))

    def _open_outstanding_of(self, party: str) -> None:
        DashboardPage(self.page).open()
        ledgers = LedgerList(self.page)
        ledgers.open()
        ledgers.open_outstanding(party)
        expect(self.page.get_by_text(f"{party}- Outstanding", exact=True)).to_be_visible(
            timeout=SCREEN_TIMEOUT_MS
        )
        expect(self._header_cell(BILL_NUMBER_HEADER)).to_be_visible(timeout=SCREEN_TIMEOUT_MS)
        Loader(self.page).wait_until_idle()

    def _rows(self) -> list[OutstandingRow]:
        """V. 4.3.600.b added Branch Name and Branch Code columns, which pushed Outstanding off screen;
        ag-Grid renders only the columns in view (OA-069, 2026-10-14). Bill numbers and amounts are read
        in two passes, scrolling to each column, and joined on the row index."""
        bill_numbers = self._column_texts(BILL_NUMBER_HEADER)
        amounts = self._column_texts(OUTSTANDING_HEADER)
        readings = []
        for row_index, bill_number in bill_numbers.items():
            amount = amounts.get(row_index, "")
            if bill_number and ANY_DIGIT.search(amount) and bill_number != GRAND_TOTAL:
                readings.append(OutstandingRow(bill_number, parse_amount(amount)))
        return readings

    def _column_texts(self, header: str) -> dict[str, str]:
        self._scroll_to(header)
        column = self._column_id(header)
        # Why the body viewport: the Grand Total footer is a row of its own with row-index 0 as well.
        rows = self._body.locator('[ref="eBodyContainer"] .ag-row')
        texts = {}
        for index in range(rows.count()):
            row = rows.nth(index)
            row_index = row.get_attribute("row-index") or str(index)
            texts[row_index] = row.locator(f'[col-id="{column}"]').inner_text().strip()
        return texts

    def _scroll_to(self, header: str) -> None:
        """Scrolls the grid sideways half a screen at a time from the left until the header is rendered."""
        # Why CSS and evaluate: the scrolling body is ag-Grid's own element, with no role or label.
        scrollbar = self._body
        scrollbar.evaluate("bar => { bar.scrollLeft = 0; }")
        for _ in range(MAX_SCROLL_STEPS):
            if appears_within(self._header_cell(header), HEADER_LOOKUP_MS):
                return
            scrollbar.evaluate("bar => { bar.scrollLeft += bar.clientWidth / 2; }")
        expect(self._header_cell(header)).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    @property
    def _body(self) -> Locator:
        return self.page.locator(".ag-body-viewport:visible").first

    def _column_id(self, header: str) -> str:
        return self._header_cell(header).get_attribute("col-id") or ""

    def _header_cell(self, header: str) -> Locator:
        # Why CSS: ag-Grid header cells carry the column's col-id, which the body cells share.
        return (
            self.page.locator(".ag-header-cell").filter(has=self.page.get_by_text(header, exact=True)).first
        )
