"""J30: Control Room > Email Settings (specs/email-sms-whatsapp-setup.md, EM-01 to EM-09).

Nothing is saved: the guard in conftest.py aborts any save or send and fails the test.
"""

import pytest

from pages.communication_setup.communication_settings import CommunicationSettings
from pages.communication_setup.email_messages import NAME_REQUIRED
from pages.communication_setup.email_settings import EmailSettings

pytestmark = [pytest.mark.p2, pytest.mark.journey("email-sms-whatsapp-setup")]

EMAIL_TEMPLATE_TYPES = (
    "Email Preference",
    "Payment Reminder",
    "Payment Received",
    "Credit Note",
    "User Invitation",
    "Purchase Order",
    "Party Statement",
    "Sale-Bill",
    "Sale Order",
    "Purchase Import Email Setup",
    "Sale Quotation",
)
SALE_BILL = "Sale-Bill"
SALE_BILL_DEFAULT_SUBJECT = "Sale-Bill Invoice"
MARG_BOOKS_SENDER = "noreply@margbooks.com"
NOT_AN_EMAIL = "not-an-email"


def test_control_room_lists_the_communication_sections(control_room: CommunicationSettings) -> None:
    control_room.expect_sections_listed(("Email Settings", "SMS Settings", "Transaction SMS"))


def test_email_settings_lists_every_template_type(email_settings: EmailSettings) -> None:
    email_settings.open()
    email_settings.expect_types_listed(EMAIL_TEMPLATE_TYPES)


def test_sale_bill_has_a_default_email_template(email_settings: EmailSettings) -> None:
    email_settings.open()
    email_settings.choose_type(SALE_BILL)
    email_settings.expect_default_template(SALE_BILL, SALE_BILL_DEFAULT_SUBJECT)


def test_email_preference_sends_from_the_marg_books_address(email_settings: EmailSettings) -> None:
    email_settings.open()
    email_settings.choose_type("Email Preference")
    email_settings.expect_default_sender(MARG_BOOKS_SENDER)


def test_new_template_without_a_name_is_not_saved(email_settings: EmailSettings) -> None:
    email_settings.open()
    email_settings.choose_type(SALE_BILL)
    template = email_settings.start_new_template()
    template.save()
    template.expect_name_flagged_with(NAME_REQUIRED)


def test_invalid_cc_address_is_refused(email_settings: EmailSettings) -> None:
    email_settings.open()
    email_settings.choose_type(SALE_BILL)
    template = email_settings.start_new_template()
    template.add_cc(NOT_AN_EMAIL)
    template.expect_cc_refused(NOT_AN_EMAIL)


def test_closing_a_new_template_discards_it(email_settings: EmailSettings, run_id: str) -> None:
    name = f"QA-{run_id}-discarded"
    email_settings.open()
    email_settings.choose_type(SALE_BILL)
    template = email_settings.start_new_template()
    template.enter_name(name)
    template.enter_subject(name)
    template.close()
    email_settings.expect_template_not_listed(name)


def test_clone_starts_from_the_default_subject_and_is_not_default(email_settings: EmailSettings) -> None:
    email_settings.open()
    email_settings.choose_type(SALE_BILL)
    clone = email_settings.clone_default_template()
    clone.expect_subject(SALE_BILL_DEFAULT_SUBJECT)
    clone.expect_not_set_as_default()
    clone.close()


def test_clone_does_not_keep_the_name_of_a_discarded_template(
    email_settings: EmailSettings, run_id: str
) -> None:
    """D2: a fresh Clone opens with an empty Name; after a discarded "+ New" it showed the discarded name."""
    email_settings.open()
    email_settings.choose_type(SALE_BILL)
    discarded = email_settings.start_new_template()
    discarded.enter_name(f"QA-{run_id}-discarded")
    discarded.close()
    clone = email_settings.clone_default_template()
    clone.expect_name("")
    clone.close()
