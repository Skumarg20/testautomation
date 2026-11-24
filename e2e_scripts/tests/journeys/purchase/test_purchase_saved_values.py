"""What a saved purchase bill holds: the totals, the list row and the reopened document.

Money is compared with values worked out here from the lines (quantity x rate, less the bill discount), not
with the figure the screen shows. The supplier is Cash Account, which carries no input tax.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.components.bill_totals import BillTotals
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label, todays_serial
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.feedback import ToastKind
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.seed_documents import SEED_PARTY, seed_draft

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

HUNDRED = Decimal(100)
TYPED_DIFFERENCE = Decimal(5)
NO_WARNING_WAIT_MS = 2_500
TYPED_VALUE_SKIP = (
    "PU-07 typed Bill Value differs from the calculated total: no doc states the rule. Jira MBC-3087, "
    "MBC-3129 and MBC-7114 (filed as a Bug) report 'bill value and invoice value showing different' as a "
    "fault, which argues against this test's expectation (typed figure posted, no warning); the code posts "
    "the typed figure (BillValueAmount handler), but live the list showed the calculated value. Question: "
    "on a mismatch, should the app warn, block the save, or post the typed figure?"
)


def _expected_invoice_value(draft: PurchaseDraft) -> Decimal:
    """Goods value (free quantity is not charged) less the bill discount; Cash Account carries no tax."""
    goods = sum((line.quantity * line.rate for line in draft.lines), Decimal(0))
    return goods - goods * draft.bill_discount / HUNDRED


def _fill_bill(bills: PurchaseBillEntryPage, draft: PurchaseDraft) -> None:
    bills.begin(draft)
    bills.enter_entry_date(draft.entry_date)
    bills.complete_header(draft)
    bills.fill_lines(draft)
    bills.footer.enter_bill_discount(draft.bill_discount)


def _find_in_list(bills: PurchaseBillEntryPage, number: str) -> None:
    bills.menu.open_purchase(PurchaseScreen.BILL)
    bills.documents.filter_this_week()
    bills.documents.find(number)
    bills.documents.expect_row_visible(number)


def test_invoice_value_is_goods_less_bill_discount(pharma_page: Page) -> None:
    bills = PurchaseBillEntryPage(pharma_page)
    draft = seed_draft(timestamp_label())

    _fill_bill(bills, draft)

    BillTotals(pharma_page).expect_invoice_value(_expected_invoice_value(draft))
    bills.discard()


def test_saved_bill_is_listed_with_its_party_and_invoice_value(pharma_page: Page) -> None:
    bills = PurchaseBillEntryPage(pharma_page)
    draft = seed_draft(timestamp_label())
    _fill_bill(bills, draft)
    number = bills.save()
    bills.expect_saved()

    _find_in_list(bills, number)

    assert bills.documents.party_of(number) == SEED_PARTY
    assert bills.documents.amount_of(number) == _expected_invoice_value(draft)
    bills.delete(number)


@pytest.mark.skip(reason=TYPED_VALUE_SKIP)
def test_typed_bill_value_is_posted_without_a_mismatch_warning(pharma_page: Page) -> None:
    """The client has no check of the typed bill value against the calculation (transactionin.component.ts,
    BillValueAmount handler); it posts the typed figure as the bill total (totaliteminvoice)."""
    bills = PurchaseBillEntryPage(pharma_page)
    draft = seed_draft(timestamp_label())
    typed_value = _expected_invoice_value(draft) + TYPED_DIFFERENCE
    _fill_bill(bills, draft)

    bills.type_bill_value(typed_value)

    assert not bills.feedback.toast_appears(ToastKind.WARNING, NO_WARNING_WAIT_MS)
    number = bills.current_number()
    bills.expect_saved()
    _find_in_list(bills, number)
    assert bills.documents.amount_of(number) == typed_value
    bills.delete(number)


def test_saved_bill_reopens_with_what_was_saved(pharma_page: Page) -> None:
    bills = PurchaseBillEntryPage(pharma_page)
    draft = seed_draft(timestamp_label())
    _fill_bill(bills, draft)
    number = bills.save()
    bills.expect_saved()
    _find_in_list(bills, number)

    bills.documents.open(number)

    bills.expect_number(number)
    bills.expect_dates(draft.entry_date, todays_serial())
    bills.grid.expect_line_carried(0, draft.lines[0])
    bills.discard()
    bills.delete(number)
