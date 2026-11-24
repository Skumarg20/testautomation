"""J21 reminders: Prescription Reminder and the report scheduler (specs/notifications-export.md, NE-31,
NE-35..NE-37). Nothing is sent and nothing is saved: the scheduler is stopped by its own validation, or
(NE-37) its save is answered by a stub; the send guard aborts WorkFlow/SchedulerSave and the SMS calls
otherwise."""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.components.app_texts import RECORD_SAVED
from pages.components.stubbed_endpoint import StubbedEndpoint, StubReply
from pages.notifications_export.delivery_endpoints import SCHEDULE_SAVE
from pages.notifications_export.json_route import success_envelope
from pages.notifications_export.prescription_reminder_page import PrescriptionReminderPage
from pages.notifications_export.schedule_setup_page import ScheduleSetupPage
from test_data.factory import DataFactory
from test_data.notifications_export import QA_EMAIL

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

PRESCRIPTION_COLUMNS = ("Patient", "Address", "Contact No.", "Due On.", "Over Due", "Prescribed By", "Sms")
PRESET_REPORT = "Minimum Stock"
INVALID_EMAIL = "qa-not-an-email"
NAME_REQUIRED = "Please Enter Schedular Name"
REPORT_REQUIRED = "Please Select Report"
INVALID_EMAIL_WARNING = "Please enter valid Email Id"
SCHEDULE_MASTER_PATH = re.compile(r"/other/Schedular$")
LIST_TIMEOUT_MS = 60_000


@pytest.fixture
def schedule_setup(journey_page: Page) -> ScheduleSetupPage:
    screen = ScheduleSetupPage(journey_page)
    screen.open()
    return screen


def test_prescription_reminder_lists_due_prescriptions_without_send_sms(journey_page: Page) -> None:
    """NE-31: the grid of due prescriptions; Send SMS stays hidden while no row is ticked."""
    reminder = PrescriptionReminderPage(journey_page)
    reminder.open()

    reminder.expect_columns(PRESCRIPTION_COLUMNS)
    reminder.expect_send_sms_hidden()


def test_schedule_without_a_name_is_refused(schedule_setup: ScheduleSetupPage) -> None:
    """NE-35: the first check is the schedule name."""
    schedule_setup.schedule()

    schedule_setup.expect_warning(NAME_REQUIRED)


def test_schedule_without_a_report_is_refused(schedule_setup: ScheduleSetupPage, data: DataFactory) -> None:
    """NE-35: with a name (Report Type comes preset), the next check is a chosen report."""
    schedule_setup.enter_name(data.party_name("Schedule"))

    schedule_setup.schedule()

    schedule_setup.expect_warning(REPORT_REQUIRED)


def test_schedule_with_an_invalid_email_is_refused(
    schedule_setup: ScheduleSetupPage, data: DataFactory
) -> None:
    """NE-36: name and report given, Email and Daily preset: a bad To address is refused."""
    schedule_setup.enter_name(data.party_name("Schedule"))
    schedule_setup.tick_report(PRESET_REPORT)
    schedule_setup.enter_to_email(INVALID_EMAIL)

    schedule_setup.schedule()

    schedule_setup.expect_warning(INVALID_EMAIL_WARNING)


def test_valid_schedule_is_saved_and_returns_to_schedule_master(
    schedule_setup: ScheduleSetupPage, data: DataFactory, journey_page: Page
) -> None:
    """NE-37 (stubbed): a schedule with name, report and a valid To address posts WorkFlow/SchedulerSave
    (answered by the stub, so nothing is ever mailed), says "Record saved successfully." and returns to
    Schedule Master (Schedular-Process.Component.ts:814-820)."""
    save = StubbedEndpoint(journey_page, SCHEDULE_SAVE)
    save.answer_with(StubReply(success_envelope(None)))
    schedule_setup.enter_name(data.party_name("Schedule"))
    schedule_setup.tick_report(PRESET_REPORT)
    schedule_setup.enter_to_email(QA_EMAIL)

    save.capture_one(schedule_setup.schedule)

    schedule_setup.expect_warning(RECORD_SAVED.pattern)
    expect(journey_page).to_have_url(SCHEDULE_MASTER_PATH, timeout=LIST_TIMEOUT_MS)
