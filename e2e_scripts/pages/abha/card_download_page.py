"""Download ABHA Card, `/abha/patient/card/download` (`abha-patient-card-download.html/.ts`).

Four ways to find the card (Mobile No. by default, `.ts:84`); each shows its own fields. "Send OTP" exists
for Mobile and Aadhaar only (`.html:171-175`); ABHA No. and ABHA Address offer two "Send Otp on ..." buttons
instead (`.html:188-195`). Every send validates the field and the captcha before calling the ABDM proxy.
"""

from enum import Enum

from playwright.sync_api import Locator, Page, expect

from pages.abha.captcha import Captcha
from pages.abha.registration_page import expect_screen_refused
from pages.base_page import BasePage

SCREEN_TIMEOUT_MS = 30_000


class DownloadMode(Enum):
    MOBILE = "mobileNo"
    AADHAAR = "aadhaar"
    ABHA_NUMBER = "abhaNo"
    ABHA_ADDRESS = "abhaAddress"


class AbhaCardDownloadPage(BasePage):
    PATH = "/abha/patient/card/download"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.captcha = Captcha(page)

    def open(self) -> None:
        self.goto(self.PATH)
        expect(self._heading).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def open_expecting_refusal(self) -> None:
        self.goto(self.PATH)
        expect_screen_refused(self.PATH, self._heading)

    def expect_heading(self) -> None:
        expect(self._heading).to_be_visible()

    def expect_every_mode_offered(self) -> None:
        for mode in DownloadMode:
            expect(self._mode(mode)).to_be_visible()

    def expect_mode_chosen(self, mode: DownloadMode) -> None:
        expect(self._mode(mode)).to_be_checked()

    def choose(self, mode: DownloadMode) -> None:
        self._mode(mode).check()

    def enter_mobile(self, mobile: str) -> None:
        self._form_field("mobileNo").fill(mobile)

    def enter_aadhaar(self, parts: tuple[str, str, str]) -> None:
        for part, digits in enumerate(parts, start=1):
            self._form_field(f"aadhaarNo{part}").fill(digits)

    def enter_abha_number_part(self, part: int, digits: str) -> None:
        self.abha_number_box(part).fill(digits)

    def enter_abha_address(self, address: str) -> None:
        self.abha_address_box.fill(address)

    def send_otp(self) -> None:
        self.page.get_by_role("button", name="Send OTP").click()

    def send_otp_to_abha_linked_mobile(self) -> None:
        self.page.get_by_role("button", name="Send Otp on ABHA linked Mobile").click()

    def submit_otp(self) -> None:
        self.page.get_by_role("button", name="Submit OTP").click()

    def close(self) -> None:
        self.page.get_by_role("button", name="Close").click()

    def expect_otp_box_shown(self) -> None:
        expect(self._form_field("otp")).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def aadhaar_box(self, part: int) -> Locator:
        return self._form_field(f"aadhaarNo{part}")

    def abha_number_box(self, part: int) -> Locator:
        return self._form_field(f"abhaNo{part}")

    @property
    def abha_address_box(self) -> Locator:
        return self._form_field("abhaAddress")

    @property
    def _heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Download ABHA Card")

    def _mode(self, mode: DownloadMode) -> Locator:
        # Why CSS: the radios sit next to bare text with no label element, so they have no accessible name
        # (`.html:21-47`); their `value` is the only stable handle.
        return self.page.locator(f'input[name="downloadtype"][value="{mode.value}"]')

    def _form_field(self, control_name: str) -> Locator:
        # Why CSS: the labels have no `for`, so the inputs have no accessible name (`.html:52-130`).
        return self.page.locator(f'input[formcontrolname="{control_name}"]')
