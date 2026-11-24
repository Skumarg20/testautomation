"""The app's full-screen spinner."""

from playwright.sync_api import expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

APPEAR_TIMEOUT_MS = 3_000
DISAPPEAR_TIMEOUT_MS = 90_000


class Loader(BasePage):
    def wait_until_idle(self) -> None:
        """Waits for the spinner to go away if it shows up; a fast screen may never show it."""
        # Why an id attribute: the spinner is an svg circle with no role, label or test id.
        spinner = self.page.locator('[id="Ellipse 363"]')
        if appears_within(spinner, APPEAR_TIMEOUT_MS):
            expect(spinner.first).to_be_hidden(timeout=DISAPPEAR_TIMEOUT_MS)
