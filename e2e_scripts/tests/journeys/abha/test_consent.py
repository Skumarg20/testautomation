"""J39 ABHA consent popup (AB-10..AB-13): validation only, so "I Agree" never gets as far as an OTP request.

Each refusal is checked to make no OTP call at all; a call the checks let through would be aborted by the
guard, never sent.
"""

import pytest

from pages.abha.consent_dialog import ConsentDialog
from pages.abha.messages import CONSENT_NAME_REQUIRED, TERMS_NOT_TICKED
from pages.abha.registration_page import AbhaRegistrationPage
from pages.components.stubbed_endpoint import StubbedEndpoint
from test_data.abha import FAKE_AADHAAR_PARTS

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]


@pytest.fixture
def consent(registration: AbhaRegistrationPage) -> ConsentDialog:
    registration.enter_aadhaar(FAKE_AADHAAR_PARTS)
    return ConsentDialog(registration.page)


def test_twelve_digits_open_the_consent_with_every_declaration_ticked(consent: ConsentDialog) -> None:
    consent.expect_shown_with_every_declaration_ticked()


def test_consent_asks_for_the_patients_name(consent: ConsentDialog) -> None:
    consent.expect_name_box_shown()


def test_consent_with_a_declaration_unticked_is_refused(
    consent: ConsentDialog, registration_otp: StubbedEndpoint
) -> None:
    consent.untick_first_declaration()

    registration_otp.expect_none_during(consent.agree)

    consent.expect_refused_with(TERMS_NOT_TICKED)


def test_consent_without_a_name_is_refused(consent: ConsentDialog, registration_otp: StubbedEndpoint) -> None:
    registration_otp.expect_none_during(consent.agree)

    consent.expect_refused_with(CONSENT_NAME_REQUIRED)


def test_consent_without_a_name_puts_the_cursor_in_the_name(consent: ConsentDialog) -> None:
    consent.agree()

    consent.expect_name_focused()


def test_closing_the_consent_requests_no_otp(
    consent: ConsentDialog, registration_otp: StubbedEndpoint
) -> None:
    registration_otp.expect_none_during(consent.close)

    consent.expect_closed()
