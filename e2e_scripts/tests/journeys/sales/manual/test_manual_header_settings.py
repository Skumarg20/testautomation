"""Manual cases 5, 142-144, 194, 195, 197-199, 205, 207, 208, 220, 221: settings that change the header.

Rules, from `processout.transaction.component.ts` / `.html` (the sale bill) in newmarg-webangular20:
- "Ask Party in Retail Billing" = Ask opens Select Party when the bill opens; Don't Ask leaves the default
  party in the field; Ask on Spacebar leaves it too and Space opens the list (:2107, :2172-2228, :3228).
- "Ask Sale Type at the time of Billing?" = Yes shows the Type field (`txtSaleType`), No hides it
  (.html:374-382).
- "Patient & Doctor Name Must" = Yes with a Cash Account party: a save without the patient warns "Please
  enter Patient Name" ("Customer" in a supermarket; :10256-10300, :10440-10444); No lets the bill save.
- "Ask patient start and save?" = Start puts the focus on the patient's mobile after the party (:3228).
- "Mode of Payment Required ?" = Yes opens Mode Of Payment on save; No saves without it.
Bills the tests save are deleted by the `saved_bills` fixture.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.sale.documents.mode_of_payment import ModeOfPayment
from pages.sale.manual.option_settings import (
    ASK_PARTY,
    ASK_PATIENT_START_SAVE,
    ASK_SALE_TYPE,
    MODE_OF_PAYMENT,
    PATIENT_DOCTOR_MUST,
    HeldOptions,
)
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.manual.saved_bills import SavedBills

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE_UNIT = Decimal(1)
PAYMENT_ABSENCE_MS = 5_000
PATIENT_NAME_ASKED = re.compile(r"Please enter (Patient|Customer) Name", re.IGNORECASE)


@dataclass(frozen=True)
class PartyAsking:
    choice: str
    opens_list: bool
    space_opens_list: bool


PARTY_ASKING = [
    pytest.param(PartyAsking("Ask", opens_list=True, space_opens_list=True), id="ask"),
    pytest.param(PartyAsking("Don't Ask", opens_list=False, space_opens_list=False), id="dont-ask"),
    pytest.param(PartyAsking("Ask on Spacebar", opens_list=False, space_opens_list=True), id="on-spacebar"),
]


@pytest.mark.parametrize("asking", PARTY_ASKING)
def test_ask_party_setting_decides_how_the_party_is_picked(
    options: HeldOptions, bill: PharmaBill, asking: PartyAsking
) -> None:
    """Rows 197 (ask), 198 (don't ask), 199 (ask on spacebar)."""
    options.hold(ASK_PARTY, asking.choice)

    bill.document.open_new()

    assert bill.document.selection.is_shown() == asking.opens_list
    if not asking.opens_list:
        expect(bill.party_field).not_to_have_value("")
    if asking.space_opens_list and not asking.opens_list:
        bill.party_field.press("Space")
        assert bill.document.selection.is_shown()


@pytest.mark.parametrize("asked", [True, False], ids=["yes", "no"])
def test_sale_type_field_follows_the_setting(options: HeldOptions, bill: PharmaBill, asked: bool) -> None:
    """Rows 220 (sale type shows in the header) and 221 (it does not)."""
    options.hold(ASK_SALE_TYPE, "Yes" if asked else "No")

    bill.document.open_new()

    if asked:
        expect(bill.sale_type_field).to_be_visible()
    else:
        expect(bill.sale_type_field).to_have_count(0)


def test_patient_asked_at_start_takes_the_focus_after_the_party(
    options: HeldOptions, bill: PharmaBill
) -> None:
    """Rows 143 and 207: focus is on the patient's mobile and stays there while it is empty."""
    options.hold(PATIENT_DOCTOR_MUST, "Yes")
    options.hold(ASK_PATIENT_START_SAVE, "Start")

    bill.open_with_party()

    expect(bill.patient_mobile_field).to_be_focused()
    bill.page.keyboard.press("Enter")
    expect(bill.patient_mobile_field).to_be_focused()


def test_missing_patient_is_refused_on_save_when_mandatory(options: HeldOptions, bill: PharmaBill) -> None:
    """Rows 5, 144 and 208: nothing is saved."""
    options.hold(PATIENT_DOCTOR_MUST, "Yes")
    options.hold(ASK_PATIENT_START_SAVE, "Save")
    bill.open_with_party()
    bill.add_line(0, ONE_UNIT)

    bill.try_save()

    bill.messages.expect_warning_like(PATIENT_NAME_ASKED)


def test_bill_saves_without_patient_when_not_mandatory(
    options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills
) -> None:
    """Rows 142 and 205: the bill saves and is listed (the fixture deletes it)."""
    options.hold(PATIENT_DOCTOR_MUST, "No")
    bill.open_with_party()
    bill.add_line(0, ONE_UNIT)

    number = saved_bills.save(bill)

    assert number


def test_payment_window_opens_on_save_when_required(options: HeldOptions, bill: PharmaBill) -> None:
    """Row 194: nothing is saved, the window is closed with Escape."""
    options.hold(MODE_OF_PAYMENT, "Yes")
    bill.start()
    bill.add_line(0, ONE_UNIT)

    bill.save()

    payment = ModeOfPayment(bill.page)
    payment.expect_open()
    bill.page.keyboard.press("Escape")


def test_no_payment_window_on_save_when_not_required(
    options: HeldOptions, bill: PharmaBill, saved_bills: SavedBills
) -> None:
    """Row 195: the bill saves straight away."""
    options.hold(MODE_OF_PAYMENT, "No")
    bill.start()
    bill.add_line(0, ONE_UNIT)

    def save_without_payment() -> None:
        bill.save()
        assert not ModeOfPayment(bill.page).is_open(timeout_ms=PAYMENT_ABSENCE_MS)
        bill.document.expect_saved()

    saved_bills.around(save_without_payment)
