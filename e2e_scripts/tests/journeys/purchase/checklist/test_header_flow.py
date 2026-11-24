"""Purchase checklist rows 2, 4, 5 and 6: the new bill page, the bill date and the party that follows it.

Rules cited: the date handler `onDateKeyUp` (Component/Transaction/InverntoryTransaction/
transactionin.component.ts:2185-2200) asks "work in this year?" for a date outside the selected financial year
(`checkFinYearValid` :2222-2232, `onFinYearDateWarning` :2233-2246) and moves the cursor to the party
(`setFocus("txtLedgerName" + tabId)` :2240-2242). Create/F2 opens the party list at once (seen live
2026-10-08, `PurchaseEntryForm._party_window_opened_by_itself`).
"""

from datetime import date

import pytest
from playwright.sync_api import expect

from pages.purchase.documents import messages
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import EXCEL_EPOCH, todays_serial
from pages.purchase.documents.fields import labelled_input

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

FINANCIAL_YEAR_STARTS_IN_MONTH = 4  # April, the Indian financial year the QA companies use


def _previous_financial_year_start() -> int:
    today = date.today()
    this_year_start = today.year if today.month >= FINANCIAL_YEAR_STARTS_IN_MONTH else today.year - 1
    return (date(this_year_start - 1, FINANCIAL_YEAR_STARTS_IN_MONTH, 1) - EXCEL_EPOCH).days


def test_new_bill_page_is_blank(empty_bill: PurchaseBillEntryPage) -> None:
    """Row 2. Whether the last three days' unsaved bills are offered (`unsave-bill`) is not asserted."""
    if empty_bill.vendor_window.is_open():
        empty_bill.vendor_window.close_with_cross()

    empty_bill.expect_vendor_empty()
    empty_bill.grid.expect_product_empty(0)


def test_start_of_the_previous_financial_year_asks_whether_to_work_in_it(
    empty_bill: PurchaseBillEntryPage,
) -> None:
    """Row 4: a date before the selected year's start gets the same question as any date outside the year."""
    empty_bill.enter_entry_date(_previous_financial_year_start())

    expect(empty_bill.page.get_by_text(messages.FINANCIAL_YEAR_CONFIRMATION)).to_be_visible()
    empty_bill.feedback.confirm_if_asked()


def test_enter_on_the_bill_date_moves_the_cursor_to_the_party(empty_bill: PurchaseBillEntryPage) -> None:
    """Row 5: an open party list also counts as the party control, as it covers the field."""
    if empty_bill.vendor_window.is_open():
        empty_bill.vendor_window.close_with_cross()

    empty_bill.enter_entry_date(todays_serial())

    party = labelled_input(empty_bill.page, "Party Name")
    assert empty_bill.vendor_window.is_open() or party.evaluate("el => el === document.activeElement")


def test_party_list_opens_after_the_bill_date(empty_bill: PurchaseBillEntryPage) -> None:
    """Row 6."""
    if empty_bill.vendor_window.is_open():
        empty_bill.vendor_window.close_with_cross()

    empty_bill.enter_entry_date(todays_serial())

    assert empty_bill.vendor_window.is_open()
