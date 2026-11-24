"""The current sign-up screen of the login app (route `/registration`, "Create your free account").

`pages/signup_page.py` describes the older layout ("Sign Up" heading, "SEND OTP" button) that the live app no
longer shows. Element names come from the live page and margweblogin `Signup/registration.component.html`.
Never press "Send OTP" with a mobile that could be real: the tests use numbers starting with 1.
"""

import re

from playwright.sync_api import Page, expect

from pages.auth.forgot_password_page import login_host
from pages.base_page import BasePage

PAGE_TIMEOUT_MS = 120_000
REGISTRATION_PATH = "/registration"
INVALID_MOBILE_MESSAGE = "Please enter a valid mobile number"


class RegistrationPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = page.get_by_role("heading", name="Create your free account", level=3)
        self.mobile = page.get_by_role("textbox", name="Enter your mobile number")
        self.send_otp = page.get_by_role("button", name="Send OTP & start free")
        self.referral_code = page.get_by_placeholder("e.g. JH245G")
        # Why CSS: the "+" that opens the referral field is an icon-only link without a name.
        self.referral_toggle = page.locator(".form-check a").first
        self.sign_in_link = page.get_by_role("link", name="Sign in here")
        self.mobile_error = page.get_by_text(INVALID_MOBILE_MESSAGE)

    def open(self) -> None:
        self.page.goto(f"{login_host()}{REGISTRATION_PATH}", timeout=PAGE_TIMEOUT_MS)
        self.expect_loaded()

    def expect_loaded(self) -> None:
        expect(self.page).to_have_url(re.compile(REGISTRATION_PATH), timeout=PAGE_TIMEOUT_MS)
        expect(self.heading).to_be_visible(timeout=PAGE_TIMEOUT_MS)
        expect(self.send_otp).to_be_visible()

    def request_otp_for(self, mobile: str) -> None:
        self.mobile.fill(mobile)
        self.send_otp.click()

    def type_mobile(self, keys: str) -> None:
        """Types key by key, so the field's input mask and maxlength apply as they do for a user."""
        self.mobile.press_sequentially(keys)

    def request_otp_with_referral(self, mobile: str, referral_code: str) -> None:
        self.referral_toggle.click()
        self.referral_code.fill(referral_code)
        self.request_otp_for(mobile)

    def expect_still_on_mobile_step(self) -> None:
        expect(self.heading).to_be_visible()
        expect(self.send_otp).to_be_visible()
