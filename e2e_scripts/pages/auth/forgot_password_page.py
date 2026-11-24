"""The "Get back into your account" screen of the login app (route `/forgetpasswordNew`).

Element ids come from margweblogin `forgetpassword/forgetPasswordnew.component.html`. Nothing here presses
"Next" with a real account: the tests only use fake identifiers (specs/password-reset-registration.md).
"""

import re

from playwright.sync_api import Page, expect

from config.settings import settings
from pages.base_page import BasePage

PAGE_TIMEOUT_MS = 120_000
RECOVERY_PATH = "/forgetpasswordNew"
CAPTCHA_FORMAT = re.compile(r"^[0-9a-z]{4}$")


class ForgotPasswordPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = page.get_by_role("heading", name="Get back into your account", level=3)
        # Why CSS: the "Mobile /Email ID" label is not tied to its input, which has only this id.
        self.user_id = page.locator("#txtEmailId")
        self.captcha = page.get_by_role("textbox", name="Captcha")
        # Why CSS: the captcha is drawn as four bare spans plus an icon link, with no role, label or test id.
        self.captcha_characters = page.locator(".captcha-box span")
        self.captcha_refresh = page.locator(".captcha-box a")
        self.captcha_error_icon = page.locator("#ErrorRef-Captcha")
        self.next_button = page.get_by_role("button", name="Next")
        self.go_back_link = page.get_by_role("link", name="Go Back")

    def open(self) -> None:
        self.page.goto(f"{login_host()}{RECOVERY_PATH}", timeout=PAGE_TIMEOUT_MS)
        self.expect_loaded()

    def expect_loaded(self) -> None:
        expect(self.heading).to_be_visible(timeout=PAGE_TIMEOUT_MS)
        expect(self.next_button).to_be_visible()

    def expect_opened_for_a_user(self) -> None:
        expect(self.page).to_have_url(re.compile(f"{RECOVERY_PATH}/.+"), timeout=PAGE_TIMEOUT_MS)
        self.expect_loaded()

    def shown_captcha(self) -> str:
        return "".join(self.captcha_characters.all_inner_texts()).replace(" ", "")

    def submit(self, user_id: str, captcha: str) -> None:
        self.user_id.fill(user_id)
        self.captcha.fill(captcha)
        self.next_button.click()

    def submit_with_shown_captcha(self, user_id: str) -> None:
        self.submit(user_id, self.shown_captcha())

    def expect_still_on_recovery(self) -> None:
        expect(self.page).to_have_url(re.compile(RECOVERY_PATH))
        expect(self.heading).to_be_visible()


def login_host() -> str:
    return settings.login_url.removesuffix("/login")
