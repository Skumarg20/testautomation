from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage

SIGN_UP = "Sign Up"
RESPONSE_TIMEOUT_MS = 90_000
SHORT_MOBILE_LENGTH = 10


class SignupPage(BasePage):
    """Registration: mobile and referral code, then an OTP sent to the mobile."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.sign_up_link = page.get_by_role("link", name=SIGN_UP)
        self.heading = page.get_by_role("heading", name=SIGN_UP, level=1)
        self.mobile = page.get_by_label("Mobile")
        self.referral_code = page.get_by_label("Referral Code")
        self.send_otp = page.get_by_role("button", name="SEND OTP")
        # Why CSS: the notifier library and the validation label expose no role or test id.
        self.error_toast = page.locator("notifier-notification.notifier__notification--error")
        self.field_error = page.locator("label.text-danger")

    def open_form(self) -> None:
        self.sign_up_link.click()
        expect(self.heading).to_be_visible()

    def request_otp(self, mobile: str, referral_code: str) -> None:
        self.mobile.fill(mobile)
        self.referral_code.fill(referral_code)
        self.send_otp.click()

    def expect_otp_step_for(self, mobile: str) -> None:
        # Why h3 role: the OTP step shows the mobile number inside a level-3 heading.
        expect(self.page.get_by_role("heading", level=3).filter(has_text=mobile)).to_be_visible()

    def expect_rejected(self, mobile: str) -> None:
        """A short mobile fails field validation; a full-length one is refused by the server."""
        if len(mobile) < SHORT_MOBILE_LENGTH:
            expect(self.field_error.first).to_be_visible()
        else:
            expect(self.error_toast.first).to_be_visible(timeout=RESPONSE_TIMEOUT_MS)

    def otp_digit(self, index: int) -> Locator:
        # Why CSS: the app numbers the OTP inputs by id only (otp_0, otp_1 ...).
        return self.page.locator(f"input[id*='otp_{index}']")
