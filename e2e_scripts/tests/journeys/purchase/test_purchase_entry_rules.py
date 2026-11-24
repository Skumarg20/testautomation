"""Purchase bill header and line rules: dates, invoice number and the refusals the app answers with.

Each test opens its own empty bill and closes it without saving, except the duplicate-number tests, which
save one bill of their own first.
"""

from datetime import date
from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from pages.accounting.confirmation import Confirmation
from pages.purchase.documents import messages
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.challan_page import PurchaseChallanPage
from pages.purchase.documents.dates import EXCEL_EPOCH, timestamp_label, todays_serial
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.feedback import ToastKind
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE
from pages.purchase.documents.seed_documents import SEED_PARTY, seed_bill

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

LONG_NUMBER = "1234567890123456789"
INVOICE_NUMBER_MAX_LENGTH = 16
FAR_PAST_DATE = (date(2000, 1, 1) - EXCEL_EPOCH).days
LONG_EXPIRED_DATE = (date(2020, 1, 31) - EXCEL_EPOCH).days
NO_DUPLICATE_WAIT_MS = 3_000
BATCH_SKIP = (
    "J05, PU-13 area (a line with no batch): the refusal text is fixed, 'Batch Required.' "
    "(transactionin.component.ts:16779), but it did not show live because the batch cell is not in "
    "edit mode after the product pick. The KB (code and docs) does not say which key or step runs the "
    "batch check. Question: on which action (Enter in the empty batch cell, leaving the row, or Save) "
    "should 'Batch Required.' appear?"
)


def test_new_bill_dates_default_to_today(new_bill: PurchaseBillEntryPage) -> None:
    new_bill.expect_dates(todays_serial(), todays_serial())


def test_entry_date_outside_the_financial_year_asks_whether_to_work_in_it(
    new_bill: PurchaseBillEntryPage,
) -> None:
    """onDateKeyUp (transactionin.component.ts) raises this confirmation for a date outside the year."""
    new_bill.enter_entry_date(FAR_PAST_DATE)

    expect(new_bill.page.get_by_text(messages.FINANCIAL_YEAR_CONFIRMATION)).to_be_visible()
    new_bill.feedback.confirm_if_asked()


def test_future_dated_entry_is_refused(new_bill: PurchaseBillEntryPage) -> None:
    new_bill.enter_entry_date(todays_serial() + 1)

    new_bill.expect_entry_date_refused(messages.FUTURE_DATE)


def test_invoice_date_after_the_entry_date_is_refused(new_bill: PurchaseBillEntryPage) -> None:
    new_bill.enter_invoice_date(todays_serial() + 1)

    new_bill.feedback.expect_toast_saying(ToastKind.WARNING, messages.INVOICE_DATE_AFTER_ENTRY_DATE)


@pytest.mark.parametrize("number", ["ABCDEF", ""], ids=["letters-only", "empty"])
def test_invoice_number_without_a_digit_is_refused(new_bill: PurchaseBillEntryPage, number: str) -> None:
    new_bill.enter_number(number)

    new_bill.feedback.expect_toast_saying(ToastKind.WARNING, messages.INVOICE_NUMBER_NEEDS_DIGITS)


def test_invoice_number_is_cut_at_sixteen_characters(new_bill: PurchaseBillEntryPage) -> None:
    new_bill.enter_number(LONG_NUMBER)

    new_bill.expect_number(LONG_NUMBER[:INVOICE_NUMBER_MAX_LENGTH])


def test_same_invoice_number_of_the_same_supplier_is_refused(pharma_page: Page) -> None:
    saved_number = seed_bill(pharma_page).number
    bills = PurchaseBillEntryPage(pharma_page)
    bills.begin(PurchaseDraft(party=SEED_PARTY, entry_date=todays_serial()))

    bills.enter_number(saved_number)

    bills.feedback.expect_toast_saying(ToastKind.WARNING, messages.NUMBER_ALREADY_EXISTS)
    bills.discard()


def test_a_challan_may_use_the_number_of_a_bill(pharma_page: Page) -> None:
    """The duplicate check is made per document type, so a challan is not blocked by a bill's number."""
    saved_number = seed_bill(pharma_page).number
    challans = PurchaseChallanPage(pharma_page)
    challans.begin(PurchaseDraft(party=SEED_PARTY, entry_date=todays_serial()))

    challans.enter_number(saved_number)

    refused = challans.feedback.toast_appears_saying(
        ToastKind.WARNING, messages.NUMBER_ALREADY_EXISTS, NO_DUPLICATE_WAIT_MS
    )
    assert not refused
    challans.discard()


@pytest.mark.skip(reason=BATCH_SKIP)
def test_line_without_a_batch_is_refused(new_bill: PurchaseBillEntryPage) -> None:
    new_bill.grid.select_product(0, STANDARD_ITEM_CODE)

    new_bill.grid.type_batch(0, "")

    new_bill.feedback.expect_toast_saying(ToastKind.WARNING, messages.BATCH_REQUIRED)


def test_expiry_before_the_entry_date_is_refused(new_bill: PurchaseBillEntryPage) -> None:
    # KB: transactionin.component.ts:12047-12052 (expiry before the bill date warns AlertMsg.expiryDateMsg);
    # the check runs only from gridNavigationOnEnterKey (:6380), so the expiry is left with Enter, not Tab.
    new_bill.grid.select_product(0, STANDARD_ITEM_CODE)
    new_bill.grid.type_batch(0, timestamp_label())

    new_bill.grid.confirm_expiry(0, LONG_EXPIRED_DATE)

    new_bill.feedback.expect_toast_saying(ToastKind.WARNING, messages.EXPIRED)


def test_zero_rate_asks_for_confirmation(new_bill: PurchaseBillEntryPage) -> None:
    new_bill.grid.select_product(0, STANDARD_ITEM_CODE)
    new_bill.grid.type_batch(0, timestamp_label())
    new_bill.grid.enter_expiry(0, todays_serial() + 400)
    new_bill.grid.enter_quantity(0, Decimal(1))

    new_bill.grid.enter_rate(0, Decimal(0))

    assert Confirmation(new_bill.page).is_asked()
    new_bill.page.get_by_text(messages.ZERO_RATE_ASKED).wait_for()
