from playwright.sync_api import expect

from pages.base_page import BasePage

APPEAR_TIMEOUT_MS = 10_000
DISAPPEAR_TIMEOUT_MS = 20_000


class Popup(BasePage):
    def expect_shown_then_dismissed(self, text: str) -> None:
        message = self.page.get_by_text(text, exact=False)
        expect(message).to_be_visible(timeout=APPEAR_TIMEOUT_MS)
        expect(message).to_be_hidden(timeout=DISAPPEAR_TIMEOUT_MS)
