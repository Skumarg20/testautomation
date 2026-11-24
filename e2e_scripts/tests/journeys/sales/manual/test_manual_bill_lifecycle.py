"""Manual cases 146-149, 152, 168: bill numbers, a refused date, closing and saving twice.

Rules cited, in newmarg-webangular20 and margbookscoreapi:
- an old date with "Sale BackDate Billing" = No warns "Back Date Billing Not Allowed" as soon as it is entered
  (processout.transaction.component.ts:1815-1816, :1866-1867; dataCalculation.ts:2694), and a save stops while
  billing is stopped (:10444);
- a second bill with a number already used is refused by the server (SaleChallanBill.cs:1895-1900; the wording
  is a language-dictionary entry, so only "a notification shows and no second bill appears" is asserted);
- a save in progress ignores a second one (`DisableSaveButton`, :10382-10385).
Every saved bill is deleted by the `saved_bills` fixture.
"""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.outstanding.document_list import DocumentList
from pages.dashboard_page import DashboardPage
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.manual import messages
from pages.sale.manual.option_settings import ASK_BILL_NO, HeldOptions
from pages.sale.manual.pharma_bill import PARTY, PharmaBill
from pages.sale.manual.saved_bills import SavedBills
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE_UNIT = Decimal(1)
BACK_BILLING = "Sale BackDate Billing"


@pytest.fixture
def back_billing_off(pharma_page: Page) -> Iterator[None]:
    """Sale BackDate Billing = No (Control Room); the tenant's original choice is put back after."""
    switch = SwitchValue(BACK_BILLING, "No")
    with switch_held(ControlRoomState(pharma_page), switch, DashboardPage(pharma_page).open):
        yield


def save_a_bill(bill: PharmaBill, saved_bills: SavedBills) -> str:
    bill.start()
    bill.add_line(0, ONE_UNIT)
    return saved_bills.save(bill)


def test_consecutive_bills_get_different_increasing_numbers(
    bill: PharmaBill, saved_bills: SavedBills
) -> None:
    """Row 147: no number is used twice and the later bill has the higher number."""
    first = save_a_bill(bill, saved_bills)
    second = save_a_bill(bill, saved_bills)

    assert int(second) > int(first)


def test_number_after_a_deletion_is_not_a_duplicate(bill: PharmaBill, saved_bills: SavedBills) -> None:
    """Row 148, partly: the configured sequence (reuse or skip the deleted number) is not written down in the
    web source, so only that the new number is listed exactly once is asserted."""
    deleted = save_a_bill(bill, saved_bills)
    SaleBillDocument(bill.page).delete(deleted)
    saved_bills.forget(deleted)

    created = save_a_bill(bill, saved_bills)

    listed = DocumentList(bill.page, SaleBillDocument.menu).numbers_for(PARTY)
    assert listed.count(created) == 1


def test_a_used_bill_number_is_refused(
    options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills
) -> None:
    """Row 149: typing the number of a saved bill into a second one saves nothing."""
    options.hold(ASK_BILL_NO, "Yes")
    used = save_a_bill(bill, saved_bills)
    bill.start()
    bill.bill_number_field.press("Control+A")
    bill.bill_number_field.press_sequentially(used)
    bill.add_line(0, ONE_UNIT)

    bill.try_save()

    bill.messages.expect_any_notification()
    bill.leave_without_saving()
    listed = DocumentList(bill.page, SaleBillDocument.menu).numbers_for(PARTY)
    assert listed.count(used) == 1


@pytest.mark.usefixtures("back_billing_off")
def test_old_date_is_refused_when_back_billing_is_off(bill: PharmaBill) -> None:
    """Row 152 (the bill is not saved: billing stops at the date)."""
    bill.start_on(date.today() - timedelta(days=1))

    bill.messages.expect_warning(messages.BACK_DATE_REFUSED)


def test_saving_twice_quickly_makes_one_bill(bill: PharmaBill, saved_bills: SavedBills) -> None:
    """Row 168: the list gains exactly one bill (`SavedBills.around` fails on any other count)."""
    bill.start()
    bill.add_line(0, ONE_UNIT)

    def press_save_twice() -> None:
        bill.double_save()
        bill.document.expect_saved()

    saved_bills.around(press_save_twice)


def test_closing_a_bill_with_data_asks_before_discarding(bill: PharmaBill) -> None:
    """Row 146: Close asks first; after Yes the bill is gone and nothing was saved."""
    bill.start()
    bill.add_line(0, ONE_UNIT)

    bill.close_with_escape_button()

    bill.expect_discard_prompt()
    bill.confirm_discard()
    bill.expect_closed()
