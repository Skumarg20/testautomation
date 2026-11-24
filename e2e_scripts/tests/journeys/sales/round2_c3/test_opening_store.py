"""Sale checklist row 7: what the bill already holds when the Select Party window opens.

Round 1 asserted the bill number only (`checklist/test_opening_focus.py`); the store half is added here.
PO = `Component/Transaction/InverntoryTransaction/processout.transaction.component.ts`.
"""

import pytest
from playwright.sync_api import expect

from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.checklist.focus import IN_A_WINDOW, PARTY
from pages.sale.checklist.sale_setting import ASK_PARTY, setting_held

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ASK = "1"  # PO:2186 "0" Don't Ask, "1" Ask, "2" Ask on Spacebar


def test_bill_number_and_store_are_filled_when_the_party_window_opens(checklist_bill: ChecklistBill) -> None:
    """Row 7. With the party asked, Enter on the bill date generates the bill number and opens "Select Party"
    (PO:2173-2176). The store was set when the bill opened: setDefaultStore (PO:4786-4835) fills the store
    name from the Control Room default store, and hides the field when the company has one store besides the
    scrap store (hideStore, PO:4826-4833). So the store field is either absent (single store) or already
    filled when the window opens; it is never shown empty."""
    checklist_bill.open_new()
    with setting_held(checklist_bill, ASK_PARTY, ASK):
        checklist_bill.reopen()

        checklist_bill.press_enter_on_date()
        checklist_bill.focus.expect_at(PARTY, IN_A_WINDOW)

        if checklist_bill.bill_number_input.count():
            expect(checklist_bill.bill_number_input.first).not_to_have_value("")
        if checklist_bill.store_input.count():
            expect(checklist_bill.store_input.first).not_to_have_value("")
        else:
            expect(checklist_bill.store_input).to_have_count(0)
