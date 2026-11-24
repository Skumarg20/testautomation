"""ABHA Registration, `/abha/patient/registration` (`abha-patient-registration.component.html/.ts`).

Three 4-digit Aadhaar boxes; the 12th digit opens the consent popup. Once the OTP request succeeds (stubbed in
tests) the screen adds Correspondence Mobile No., OTP and a captcha. Its labels are not linked to the inputs,
so the inputs are found by their Angular form-control names.
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.abha.captcha import Captcha
from pages.base_page import BasePage
from pages.masters.master_toasts import MasterToasts

SCREEN_TIMEOUT_MS = 30_000
AADHAAR_PARTS = ("adharNo1", "adharNo2", "adharNo3")
RESEND_LIMIT = re.compile(r"Upto\s+2\s+times")
MOBILE_NOTE = "Note: This mobile number will be used for all the communications related to ABHA"


class ScreenNotRefusedError(AssertionError):
    def __init__(self, path: str) -> None:
        super().__init__(f"{path} opened for a company that must not see ABHA (AB-05, decision N2)")


def expect_screen_refused(path: str, screen: Locator) -> None:
    """The screen must not render: refused, redirected or blank (pack AB-05). Waits the full load time for
    it, so a screen that does open is caught and not missed because it had not rendered yet."""
    try:
        expect(screen).to_be_visible(timeout=SCREEN_TIMEOUT_MS)
    except AssertionError:
        return
    raise ScreenNotRefusedError(path)


class AbhaRegistrationPage(BasePage):
    PATH = "/abha/patient/registration"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.captcha = Captcha(page)

    def open(self) -> None:
        self.goto(self.PATH)
        expect(self._sub_heading).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def open_expecting_refusal(self) -> None:
        self.goto(self.PATH)
        expect_screen_refused(self.PATH, self._sub_heading)

    def expect_headings(self) -> None:
        expect(self.page.get_by_role("heading", name="Ayushman Bharat Health Account")).to_be_visible()
        expect(self._sub_heading).to_be_visible()

    def expect_three_aadhaar_boxes(self) -> None:
        for part in range(len(AADHAAR_PARTS)):
            expect(self.aadhaar_box(part)).to_be_visible()

    def expect_download_link(self) -> None:
        expect(self.page.get_by_role("link", name="Download ABHA Card")).to_be_visible()

    def type_into_aadhaar_box(self, part: int, text: str) -> None:
        self.aadhaar_box(part).press_sequentially(text)

    def enter_aadhaar(self, parts: tuple[str, str, str]) -> None:
        """Typing the last digit opens the consent popup (`.ts:131-135`)."""
        for part, digits in enumerate(parts):
            self.type_into_aadhaar_box(part, digits)

    def show_aadhaar(self) -> None:
        # Why CSS: the eye icon is a bare svg with a click handler, no role or name (`.html:50-59`).
        self.page.locator("svg.iconPosi").first.click()

    def enter_correspondence_mobile(self, mobile: str) -> None:
        self._form_field("CpdMno").fill(mobile)

    def type_otp(self, otp: str) -> None:
        self.otp_box.press_sequentially(otp)

    def submit(self) -> None:
        self.page.get_by_role("button", name="Submit").click()

    def close(self) -> None:
        self.page.get_by_role("button", name="Close").click()

    def expect_refused_with(self, message: re.Pattern[str]) -> None:
        MasterToasts(self.page).expect_warning_saying(message)

    def expect_otp_stage(self) -> None:
        expect(self._form_field("CpdMno")).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def expect_resend_limit_shown(self) -> None:
        expect(self.page.get_by_text(RESEND_LIMIT)).to_be_visible()

    def expect_mobile_note_shown(self) -> None:
        expect(self.page.get_by_text(MOBILE_NOTE)).to_be_visible()

    def aadhaar_box(self, part: int) -> Locator:
        return self._form_field(AADHAAR_PARTS[part])

    @property
    def otp_box(self) -> Locator:
        return self._form_field("otp")

    @property
    def _sub_heading(self) -> Locator:
        return self.page.get_by_role("heading", name="ABHA Registration")

    def _form_field(self, control_name: str) -> Locator:
        # Why CSS: the labels have no `for`, so the inputs have no accessible name (`.html:17-77`).
        return self.page.locator(f'input[formcontrolname="{control_name}"]')
