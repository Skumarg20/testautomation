"""Sale checklist rows 2, 3, 6, 7, 11, 12: where the cursor is when a new sale bill opens and moves on.

Source of every expectation is the Angular component of the sale bill, `processout.transaction.component.ts`
(PO) and its template; the line numbers are from the checkout of 2026-10-19. Nothing is saved.
"""

import re
from dataclasses import dataclass

import pytest
from playwright.sync_api import expect

from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.checklist.focus import (
    BILL_DATE,
    BILL_NUMBER,
    IN_A_WINDOW,
    PARTY,
    PATIENT_MOBILE,
    SALE_TYPE,
    STORE,
    grid_column,
)
from pages.sale.checklist.holds import HoldDateBilling
from pages.sale.checklist.sale_setting import ASK_PARTY, setting_held
from pages.sale.documents.item_grid import PRODUCT
from pages.settings.control_room import DateBilling, YesNo

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ASK = "1"  # PO:3228 and PO:2186: "0" Don't Ask (cash party is taken), "1" Ask, "2" Ask on Spacebar
BACK_DATE: DateBilling = "Sale BackDate Billing"
FUTURE_DATE: DateBilling = "Sale Future Date Billing"
AFTER_PARTY = (
    BILL_NUMBER,
    PATIENT_MOBILE,
    STORE,
    SALE_TYPE,
    grid_column(PRODUCT),
    grid_column("barcode"),
    IN_A_WINDOW,
)


def test_new_bill_shows_one_empty_first_grid_row(bill: ChecklistBill) -> None:
    """Row 2: Create opens a bill whose grid has its default blank line (PO ngAfterViewInit adds the
    default row), with no product in it and no second row yet."""
    bill.expect_grid_ready()

    expect(bill.product_cell(0)).to_have_text(re.compile(r"^\s*$"))
    expect(bill.document.grid.cell(1, PRODUCT)).to_have_count(0)


@dataclass(frozen=True)
class OpeningCase:
    back: YesNo
    future: YesNo
    on_bill_date: bool


@pytest.mark.parametrize(
    "case",
    [OpeningCase("Yes", "No", True), OpeningCase("No", "Yes", True), OpeningCase("No", "No", False)],
    ids=["back-on", "future-on", "both-off"],
)
def test_focus_on_opening_depends_on_the_date_billing_settings(
    hold_date_billing: HoldDateBilling, screen: ChecklistBill, case: OpeningCase
) -> None:
    """Row 3: the cursor starts on the bill date only while back or future billing is allowed; with both
    off the bill date is skipped and the party takes the cursor (PO:1050-1062, checkdatevalidation)."""
    hold_date_billing(BACK_DATE, case.back)
    hold_date_billing(FUTURE_DATE, case.future)

    screen.open_new()

    if case.on_bill_date:
        screen.focus.expect_at(BILL_DATE)
    else:
        screen.focus.expect_at(PARTY, IN_A_WINDOW)


def test_enter_on_bill_date_moves_to_the_series_window_or_the_party(
    hold_date_billing: HoldDateBilling,
    screen: ChecklistBill,
) -> None:
    """Row 6: Enter on a valid bill date goes on to the party; the multi-series window opens first only when
    the company has several series (PO:1791-1850 onDateKeyUp; PO:6195-6216 opens the series list when the
    bill-number call answers IsMulti, else focuses txtLedgerName)."""
    hold_date_billing(BACK_DATE, "Yes")
    screen.open_new()
    screen.focus.expect_at(BILL_DATE)

    screen.press_enter_on_date()

    screen.focus.expect_at(PARTY, IN_A_WINDOW)


def test_bill_number_is_filled_before_the_party_window_opens(bill: ChecklistBill) -> None:
    """Row 7: with the party being asked, the bill number is generated before the "Select Party" window shows
    (PO:2173-2176 windowkeyHandler calls generateBillNo() while the number is empty, then opens the window).
    Whether the store is also filled by then is not stated in the source; it is not asserted."""
    with setting_held(bill, ASK_PARTY, ASK):
        bill.reopen()
        if not bill.bill_number_input.is_visible():
            pytest.skip("row 7: needs a sale bill that shows a bill number field")

        bill.press_enter_on_date()
        bill.focus.expect_at(PARTY, IN_A_WINDOW)

        expect(bill.bill_number_input).not_to_have_value("")


def test_after_the_party_the_cursor_goes_to_the_next_header_stop_or_the_grid(bill: ChecklistBill) -> None:
    """Row 12: after the party is chosen the cursor never stays on the party: it goes to the bill number
    (Ask Bill No. = Yes), the patient, the store, the sale type, a pending-documents window, or the first
    grid cell (PO:2205-2244 and SaleSettingbasedNavigation PO:5977-6007)."""
    with setting_held(bill, ASK_PARTY, ASK):
        bill.reopen()

        bill.choose_standard_party()

        bill.focus.expect_at(*AFTER_PARTY)
        assert not bill.focus.is_at(PARTY)


def test_store_is_reached_before_the_grid_when_the_company_has_several_stores(bill: ChecklistBill) -> None:
    """Row 11: with more than one store the cursor stops on the store after the party, before the product
    (PO:5990-5991 and PO:2234: txtStore is focused when isStoreVisible && isCursorWaitOnStore())."""
    with setting_held(bill, ASK_PARTY, ASK):
        bill.reopen()
        if not bill.store_input.is_visible():
            pytest.skip("row 11: needs a company with more than one store (the store field is not shown)")

        bill.choose_standard_party()

        bill.focus.press_until("Enter", (STORE, grid_column(PRODUCT)), limit=6)
        assert bill.focus.is_at(STORE)
