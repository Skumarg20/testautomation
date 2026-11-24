import re

from playwright.sync_api import Page, expect

from config.settings import LoginStyle, settings
from pages.base_page import BasePage

LOGIN_TIMEOUT_MS = 150_000


class LoginPage(BasePage):
    """Element ids come from the Marg login app. Single-step is UAT/preprod; two-step is production style."""

    def __init__(self, page: Page, style: LoginStyle = settings.login_style) -> None:
        super().__init__(page)
        self.style = style
        self.user_id = page.locator("#userid")
        self.continue_button = page.locator("#SIGNin")
        self.password = page.locator("input#password")
        self.password_error_icon = page.locator("#ErrorRef-Password")
        self.submit_two_step = page.locator('[type="submit"]')
        self.submit_single_step = page.locator("#btnSave")

    def open(self) -> None:
        self.page.goto(settings.login_url)
        self.page.wait_for_load_state("load")

    def sign_in(self, user: str, password: str) -> None:
        if self.style == "single_step":
            self._sign_in_single_step(user, password)
        else:
            self._sign_in_two_step(user, password)

    def _sign_in_single_step(self, user: str, password: str) -> None:
        self.user_id.fill(user)
        self.password.fill(password)
        self.submit_single_step.click()

    def _sign_in_two_step(self, user: str, password: str) -> None:
        self.continue_with_user(user)
        self.password.wait_for(state="visible")
        self.submit_password(password)

    def continue_with_user(self, user: str) -> None:
        """Step 1 of the two-step login: type the user id (may be empty) and press SIGN IN."""
        self.user_id.fill(user)
        self.continue_button.click()

    def submit_password(self, password: str) -> None:
        """Step 2: type the password (may be empty) and press CONTINUE."""
        self.password.fill(password)
        self.submit_two_step.click()

    def expect_message(self, text: str) -> None:
        expect(self.page.get_by_text(text)).to_be_visible()

    def expect_on_login_host(self) -> None:
        expect(self.page).to_have_url(re.compile(re.escape(settings.login_url)), timeout=LOGIN_TIMEOUT_MS)

    def expect_password_step(self) -> None:
        expect(self.password).to_be_visible()
