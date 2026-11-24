"""Report > Statutory Report > E-Invoice: the "E-Invoice Summary" list of bills to upload to the IRP.

Safety: this page object only filters, reads and ticks rows. It deliberately has no method that presses
Generate, Get IRN, Manual or Cancel, because those submit to the government IRP through a GSP and nothing
proves the QA tenant is wired to a sandbox (spec `specs/e-invoice.md`, Q-EI-1).
"""

import re
from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.screen import DocumentScreen

EInvoiceStatus = Literal["All", "Uploaded", "Pending", "Cancelled"]
EInvoicePeriod = Literal[
    "Today", "This Month", "Yesterday", "Last 7 Days", "This Week", "Previous Month", "This Year", "Custom"
]

HEADING = "E-Invoice Summary"
STATUSES: tuple[EInvoiceStatus, ...] = ("All", "Uploaded", "Pending", "Cancelled")
LIST_TIMEOUT_MS = 60_000
COUNTER = re.compile(r"Uploaded-\s*(\d+)\s*Pending-\s*(\d+)\s*Cancelled-\s*(\d+)")
PENDING_GROUP = 2


@dataclass(frozen=True)
class EInvoiceBill:
    """One bill as the summary grid shows it, every value as on-screen text."""

    customer: str
    gstin: str
    tax_type: str
    invoice_date: str
    invoice_no: str
    bill_amount: str
    taxable_value: str
    tax_amount: str

    def cells(self) -> list[str]:
        return [
            self.customer,
            self.gstin,
            self.tax_type,
            self.invoice_date,
            self.invoice_no,
            self.bill_amount,
            self.taxable_value,
            self.tax_amount,
        ]


class EInvoiceSummaryPage(BasePage):
    def open(self) -> None:
        """Opens the screen through the side menu; a full page load would restart the app's session."""
        DocumentScreen(self.page).open_menu(("Report",))
        self.page.get_by_role("tab", name="Statutory Report").click()
        self.page.get_by_role("link", name="E-Invoice", exact=True).click()
        expect(self._heading).to_be_visible(timeout=LIST_TIMEOUT_MS)

    def choose_period(self, period: EInvoicePeriod) -> None:
        self._period_select.select_option(period)

    def choose_status(self, status: EInvoiceStatus) -> None:
        self._status_select.select_option(status)

    def include_b2b_and_cdnr(self) -> None:
        self._b2b.check()
        self._cdnr.check()

    def submit(self) -> None:
        self.page.get_by_role("main").get_by_role("button", name="Submit").click()

    def show_b2b_and_cdnr_bills(self, period: EInvoicePeriod, status: EInvoiceStatus) -> None:
        self.choose_period(period)
        self.choose_status(status)
        self.include_b2b_and_cdnr()
        self.submit()

    def select_bill(self, invoice_no: str) -> None:
        self._selection_box(invoice_no).click()

    def expect_status_choices(self) -> None:
        expect(self._status_select.locator("option")).to_have_text(list(STATUSES))

    def expect_document_types_unticked(self) -> None:
        expect(self._b2b).not_to_be_checked()
        expect(self._cdnr).not_to_be_checked()

    def expect_columns(self, headers: tuple[str, ...]) -> None:
        names = self.page.get_by_role("main").get_by_role("columnheader")
        for header in headers:
            expect(names.filter(has_text=header)).to_have_count(1)

    def expect_period_dates(self, start: str, end: str) -> None:
        expect(self.page.locator("input#txtfromDate")).to_have_value(start)
        expect(self.page.locator("input#txttoDate")).to_have_value(end)

    def expect_bill_listed(self, bill: EInvoiceBill) -> None:
        row = self._row(bill.invoice_no)
        expect(row).to_be_visible(timeout=LIST_TIMEOUT_MS)
        expect(row.get_by_role("gridcell").filter(has_text=re.compile(r"\S"))).to_have_text(bill.cells())

    def expect_bill_not_listed(self, invoice_no: str) -> None:
        """Use after the bill was listed once, so the check waits for the refreshed list to drop it."""
        expect(self._row(invoice_no)).to_have_count(0, timeout=LIST_TIMEOUT_MS)

    def expect_actions_offered(self, actions: tuple[str, ...]) -> None:
        main = self.page.get_by_role("main")
        for action in actions:
            expect(main.get_by_role("button", name=action, exact=True)).to_be_visible()

    def expect_actions_hidden(self, actions: tuple[str, ...]) -> None:
        main = self.page.get_by_role("main")
        for action in actions:
            expect(main.get_by_role("button", name=action, exact=True)).to_be_hidden()

    def pending_count(self) -> int:
        self._expect_counter_shown()
        match = COUNTER.search(self._counter.inner_text())
        if match is None:
            raise AssertionError(
                f'Counter "{self._counter.inner_text()}" is not "Uploaded- n Pending- n ..."'
            )
        return int(match.group(PENDING_GROUP))

    def _expect_counter_shown(self) -> None:
        expect(self._counter).to_be_visible(timeout=LIST_TIMEOUT_MS)

    @property
    def _heading(self) -> Locator:
        return self.page.get_by_role("heading", name=HEADING)

    @property
    def _counter(self) -> Locator:
        return self.page.get_by_role("main").get_by_role("paragraph").filter(has_text=COUNTER)

    # The filter controls have no labels or names; their ids are the only stable handle (spec Locators).
    @property
    def _period_select(self) -> Locator:
        return self.page.locator("select#txtdateType")

    @property
    def _status_select(self) -> Locator:
        return self.page.locator("select#txtDatadropdown")

    @property
    def _b2b(self) -> Locator:
        return self.page.locator("input#b2b")

    @property
    def _cdnr(self) -> Locator:
        return self.page.locator("input#cdnr")

    def _row(self, invoice_no: str) -> Locator:
        cell = self.page.get_by_role("gridcell", name=invoice_no, exact=True)
        return self.page.get_by_role("main").get_by_role("row").filter(has=cell)

    def _selection_box(self, invoice_no: str) -> Locator:
        # ag-Grid renders a hidden selection box in every cell; only the first cell's is shown.
        return self._row(invoice_no).locator(".ag-selection-checkbox").first
