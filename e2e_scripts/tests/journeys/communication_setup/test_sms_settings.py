"""J30: Control Room > SMS Settings, DLT registration popup (specs/email-sms-whatsapp-setup.md, SM-01, SM-07).

DLT Save is never pressed (spec N2); the guard in conftest.py fails the test on any save or send.
"""

import pytest

from pages.communication_setup.dlt_registration import DltDetails, DltRegistration

pytestmark = [pytest.mark.p2, pytest.mark.journey("email-sms-whatsapp-setup")]

# Not a real DLT registration: values only typed into the popup and cancelled.
UNSAVED_DETAILS = DltDetails(registered_number="1234567890", sender_id="QATEST")


def test_cancelled_dlt_details_are_not_kept(dlt_registration: DltRegistration) -> None:
    dlt_registration.open()
    original = dlt_registration.current_details()
    dlt_registration.enter(UNSAVED_DETAILS)
    dlt_registration.cancel()
    dlt_registration.open()
    dlt_registration.expect_details(original)
    dlt_registration.cancel()
