"""Registration cases, disabled upstream (the `register` sheet is not in sat.list.ts)."""

import json

import pytest
from playwright.sync_api import Page

from pages.signup_page import SignupPage
from test_data.document_cases import CASES_FILE, DocumentCase, case_id

SKIP_REASON = (
    "RG-08 / RG-05 / RG-03 (register sheet TC_001-TC_003, disabled upstream in sat.list.ts): a first "
    "sign-up sends an OTP to an Indian mobile (onedrive:Signup_Login & Company_creation_v1.0.docx#1), and "
    "typing a mobile already calls sendOtp (registration.component.ts:1491-1493, onMobileNumberInput), so "
    "the real-format numbers in TC_001/TC_002 could text a real person. Must not run as is. Question: "
    "which mobile range and referral code are reserved for QA (or is there an OTP stub), and should the "
    "register sheet be re-enabled?"
)
MODULE = "authentication"
SHEET = "register"

pytestmark = [pytest.mark.p1, pytest.mark.journey("auth")]


def _register_cases() -> list[DocumentCase]:
    records = json.loads(CASES_FILE.read_text())
    return [
        DocumentCase(**{**record, "line_items": tuple(record["line_items"])})
        for record in records
        if record["module"] == MODULE and record["sheet"] == SHEET
    ]


@pytest.mark.skip(reason=SKIP_REASON)
@pytest.mark.parametrize("case", _register_cases(), ids=case_id)
def test_registration_case(page: Page, case: DocumentCase, base_url: str) -> None:
    mobile = case.inputs.get("mobile", "")
    signup = SignupPage(page)
    page.goto(base_url)
    signup.open_form()

    signup.request_otp(mobile, case.inputs.get("referral_code", ""))

    if case.type.upper() == "POSITIVE":
        signup.expect_otp_step_for(mobile)
    else:
        signup.expect_rejected(mobile)
