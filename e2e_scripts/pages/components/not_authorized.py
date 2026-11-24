"""The app's not-authorized screen, rendered for unknown routes and for pages the role may not open."""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

NOT_AUTHORIZED_HEADING = "Oops! You are not authorized."
# The app first loads its shell, then resolves the route and swaps in this screen.
NOT_AUTHORIZED_TIMEOUT_MS = 60_000


class NotAuthorizedPage(BasePage):
    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", name=NOT_AUTHORIZED_HEADING, exact=True)

    def expect_shown(self) -> None:
        expect(self.heading).to_be_visible(timeout=NOT_AUTHORIZED_TIMEOUT_MS)
