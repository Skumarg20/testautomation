"""J39 linking an ABHA to a sale bill (AB-32 linked state, AB-33, AB-34) and "Patient History" (AB-35).

No ABHA row is seeded and no ABHA-linked bill is saved (decision N3): the patient's ABHA rows come from a
proven stub, the save of an ABHA-linked bill is answered by a stub that refuses it (only its request body is
read), and the reopened-bill check patches the server's reply for a plain saved bill. "Patient History"
opens the external consent site in a new tab, answered by a stub (`pages/abha/consent_connector.py`).
"""

import pytest

from pages.abha.bill_abha_link import (
    BILL_NOT_SAVED_REPLY,
    BILL_SAVE,
    SavedBillAbhaPatch,
    abha_link_in,
)
from pages.abha.billing_details import AbhaBillingDetails
from pages.abha.cash_bill_draft import CashBillDraft
from pages.abha.consent_connector import ConsentConnectorStub
from pages.abha.sale_bill_abha import SaleBillAbha
from pages.components.stubbed_endpoint import StubbedEndpoint
from test_data.abha import FAKE_ABHA_NUMBER, FAKE_ABHA_ROW, FAKE_ABHA_ROW_LINKID

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]

FAKE_ABHA_ROW_ADDRESS = str(FAKE_ABHA_ROW["abhaaddress"])


def test_select_abha_address_lists_the_patients_abha_rows(billing_details: AbhaBillingDetails) -> None:
    billing_details.expect_row(FAKE_ABHA_NUMBER, FAKE_ABHA_ROW_ADDRESS)


def test_choosing_an_abha_row_turns_the_button_green(abha_linked_sale_bill: SaleBillAbha) -> None:
    abha_linked_sale_bill.expect_button_offered_as_linked()


def test_linked_bill_offers_to_change_the_abha_address(abha_linked_sale_bill: SaleBillAbha) -> None:
    abha_linked_sale_bill.open_selection()

    abha_linked_sale_bill.expect_change_address_offered()


def test_bill_save_sends_the_chosen_abha(cash_bill_with_abha: CashBillDraft) -> None:
    save = StubbedEndpoint(cash_bill_with_abha.page, BILL_SAVE)
    save.answer_with(BILL_NOT_SAVED_REPLY)

    sent = abha_link_in(save.capture_one(cash_bill_with_abha.press_save).json_body())

    assert (sent["patientAbhaLinkId"], sent["abhano"], sent["abhaaddress"]) == (
        FAKE_ABHA_ROW_LINKID,
        FAKE_ABHA_NUMBER,
        FAKE_ABHA_ROW_ADDRESS,
    )


def test_reopened_bill_with_an_abha_link_shows_the_green_button(abha_page_cash_bill: CashBillDraft) -> None:
    entry_number = abha_page_cash_bill.save()
    patch = SavedBillAbhaPatch(abha_page_cash_bill.page, FAKE_ABHA_ROW)
    patch.install()

    patch.capture_patched(lambda: abha_page_cash_bill.reopen(entry_number))

    SaleBillAbha(abha_page_cash_bill.page).expect_button_offered_as_linked()


def test_patient_history_opens_the_consent_site_in_a_new_tab(
    abha_sale_bill: SaleBillAbha, consent_connector: ConsentConnectorStub
) -> None:
    abha_sale_bill.open_selection()

    consent_connector.expect_consent_tab_from(abha_sale_bill.choose_patient_history)


def test_patient_history_leaves_the_bill_without_an_abha(
    abha_sale_bill: SaleBillAbha, consent_connector: ConsentConnectorStub
) -> None:
    abha_sale_bill.open_selection()
    consent_connector.expect_consent_tab_from(abha_sale_bill.choose_patient_history)

    abha_sale_bill.expect_button_offered_as_unlinked()
