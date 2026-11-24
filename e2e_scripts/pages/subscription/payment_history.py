"""The Payment History tab: one entry per payment ("Success ₹ 2,500.00" over "<timestamp> | TXN ID: <id>"),
the detail of the selected entry, a Search box and a Time Period select."""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.subscription.rupees import rupees_in

HISTORY_TIMEOUT_MS = 30_000
ENTRY_HEADING = re.compile(r"^(?P<status>\w+) (?P<amount>₹ [\d,]+\.\d{2})$")
ENTRY_LINE = re.compile(r"^(?P<paid_at>\d{4}-\d{2}-\d{2} [\d:.]+Z) \| TXN ID: (?P<txn_id>\d+)$")
INVOICE_DATE_LABEL = "Invoice Date-"
LONGEST_PERIOD = "Last 3 Month"


@dataclass(frozen=True)
class PaymentEntry:
    status: str
    amount: Decimal
    paid_at: str
    txn_id: str


@dataclass(frozen=True)
class PaymentDetail:
    amount: Decimal
    invoice_date: str


class PaymentHistory(BasePage):
    def show_longest_period(self) -> None:
        self.page.get_by_role("main").get_by_role("combobox").select_option(label=LONGEST_PERIOD)

    def entries(self) -> list[PaymentEntry]:
        expect(self._entry_headings.first).to_be_visible(timeout=HISTORY_TIMEOUT_MS)
        return [_entry(heading) for heading in self._entry_headings.all()]

    def select(self, index: int) -> None:
        self._entry_headings.nth(index).click()

    def detail(self) -> PaymentDetail:
        amount_heading = self.page.get_by_role("main").get_by_role("heading", level=2).filter(has_text="₹")
        invoice_line = self.page.get_by_role("main").get_by_text(INVOICE_DATE_LABEL)
        return PaymentDetail(
            amount=rupees_in(amount_heading.inner_text()),
            invoice_date=invoice_line.inner_text().replace(INVOICE_DATE_LABEL, "", 1).strip(),
        )

    def expect_detail_for(self, entry: PaymentEntry) -> None:
        expect(self.page.get_by_role("main").get_by_text(INVOICE_DATE_LABEL)).to_contain_text(entry.paid_at)

    def search(self, text: str) -> None:
        box = self.page.get_by_role("main").get_by_role("searchbox", name="Search")
        box.fill(text)
        box.press("Enter")

    def expect_no_entries(self) -> None:
        expect(self._entry_headings).to_have_count(0, timeout=HISTORY_TIMEOUT_MS)

    @property
    def _entry_headings(self) -> Locator:
        return self.page.get_by_role("main").get_by_role("heading", level=1).filter(has_text="₹")


def _entry(heading: Locator) -> PaymentEntry:
    title = _matched(ENTRY_HEADING, heading.inner_text())
    line = _matched(ENTRY_LINE, heading.locator("..").get_by_role("paragraph").inner_text())
    return PaymentEntry(title["status"], rupees_in(title["amount"]), line["paid_at"], line["txn_id"])


def _matched(pattern: re.Pattern[str], text: str) -> re.Match[str]:
    found = pattern.match(" ".join(text.split()))
    if found is None:
        raise ValueError(f'Payment entry text "{text}" does not match {pattern.pattern}')
    return found
