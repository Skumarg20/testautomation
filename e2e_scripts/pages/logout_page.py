from playwright.sync_api import Page, expect

from pages.base_page import BasePage

LOGOUT_TIMEOUT_MS = 20_000


class LogoutPage(BasePage):
    """The profile menu of a signed-in screen and the login screen it returns to."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # Why id: the header menu button has no test id or accessible name (same id as DashboardPage.log_out).
        self.profile_menu = page.locator("#dropdownMenuButton")
        self.logout_item = page.get_by_text("Logout", exact=True)

    def log_out(self) -> None:
        self.profile_menu.click()
        self.logout_item.click()

    def expect_signed_out(self) -> None:
        expect(self.profile_menu).to_be_hidden(timeout=LOGOUT_TIMEOUT_MS)
