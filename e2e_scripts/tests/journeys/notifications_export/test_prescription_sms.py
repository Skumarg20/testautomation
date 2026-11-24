"""J21 Prescription Reminder with prescriptions (specs/notifications-export.md, NE-32..NE-34), on the pharma
(chemist trade) company. Send SMS goes to stubs of RegisterUser/SendBulkSMSTemplate and
Reports/InsertBulkReminderData; nothing is sent. NE-34 saves a patient, a prescription and a sale bill that
cannot be deleted from here, so it runs only with --allow-permanent."""

import re

import pytest
from playwright.sync_api import Page

from pages.accounting.toasts import Toasts
from pages.components.stubbed_endpoint import StubbedEndpoint, StubReply
from pages.notifications_export.delivery_endpoints import REMINDER_RECORD, SMS_SEND
from pages.notifications_export.json_route import success_envelope
from pages.notifications_export.patient_bill import PatientBill
from pages.notifications_export.patient_form import PatientForm
from pages.notifications_export.prescription_master_page import PrescriptionMasterPage
from pages.notifications_export.prescription_reminder_page import PrescriptionReminderPage
from test_data.factory import DataFactory
from test_data.sale_items import DOLO_650

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("notifications-export"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SMS_SENT = re.compile(re.escape("SMS send successfully"), re.IGNORECASE)
# Pres. Date starts at today; the shortest course makes the prescription fall due first.
DUE_IN_DAYS = 1
PERMANENT_DATA = "a patient, a prescription and a cash sale bill on the pharma company"


@pytest.fixture
def due_reminders(pharma_page: Page) -> PrescriptionReminderPage:
    reminder = PrescriptionReminderPage(pharma_page)
    reminder.open()
    if not reminder.has_due_prescriptions():
        pytest.skip("NE-32/NE-33: needs a due prescription on the pharma company")
    return reminder


@pytest.fixture
def prescribed_patient(pharma_page: Page, data: DataFactory) -> str:
    """A new patient with a new prescription of one item, due after DUE_IN_DAYS."""
    patient = data.party_name("Patient")
    PatientForm(pharma_page).add(patient)
    prescription = PrescriptionMasterPage(pharma_page)
    prescription.open_new()
    prescription.enter_days(DUE_IN_DAYS)
    prescription.choose_patient(patient)
    prescription.add_item(DOLO_650.description)
    prescription.save()
    return patient


def test_ticking_a_due_prescription_offers_send_sms(due_reminders: PrescriptionReminderPage) -> None:
    """NE-32: Send SMS appears once a row is ticked (it is not clicked)."""
    due_reminders.tick_first_prescription()

    due_reminders.expect_send_sms_offered()


def test_send_sms_sends_and_records_the_reminder(
    due_reminders: PrescriptionReminderPage, pharma_page: Page
) -> None:
    """NE-33 (stubbed): Send SMS posts the messages, then records the reminder, then says
    "SMS send successfully" (code; the KB says "SMS Sent Successfully", K6)."""
    sms = StubbedEndpoint(pharma_page, SMS_SEND)
    sms.answer_with(StubReply(success_envelope(None)))
    record = StubbedEndpoint(pharma_page, REMINDER_RECORD)
    record.answer_with(StubReply(success_envelope(None)))
    due_reminders.tick_first_prescription()

    sms.capture_one(due_reminders.send_sms)

    assert record.answered_once_things_settle() == 1
    Toasts(pharma_page).expect_any_saying(SMS_SENT)


@pytest.mark.permanent(PERMANENT_DATA)
def test_saved_prescription_is_listed_for_reminder(prescribed_patient: str, pharma_page: Page) -> None:
    """NE-34: a prescription saved by the test appears in the reminder list."""
    reminder = PrescriptionReminderPage(pharma_page)

    reminder.open()

    reminder.expect_listed(prescribed_patient)


@pytest.mark.permanent(PERMANENT_DATA)
def test_prescription_leaves_the_reminder_list_after_a_sale_bill(
    prescribed_patient: str, pharma_page: Page
) -> None:
    """NE-34 (MB-035643): once a sale bill is made for the patient, the reminder is gone."""
    PatientBill(pharma_page).make(prescribed_patient, DOLO_650)
    reminder = PrescriptionReminderPage(pharma_page)

    reminder.open()

    reminder.expect_not_listed(prescribed_patient)
