"""The browser-made captcha both standalone ABHA screens show above their send/submit buttons.

Four characters are drawn from `[0, 1, a, b, 4, c, 1, d, f, h, 5, 9]` in the browser
(`abha-patient-registration.component.ts:88-99`, `abha-patient-card-download.ts:102-113`) and rendered as
four spans; the screen compares the typed text with them (pack finding 3).
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

# No character of the captcha alphabet is a "z", so this can never match.
WRONG_CAPTCHA = "zzzz"


class Captcha(BasePage):
    def enter(self, text: str) -> None:
        self.field.fill(text)

    def enter_shown_code(self) -> None:
        self.enter(self.shown_code())

    def shown_code(self) -> str:
        return "".join(part.strip() for part in self._characters.all_inner_texts())

    def expect_focused(self) -> None:
        expect(self.field).to_be_focused()

    @property
    def field(self) -> Locator:
        return self.page.get_by_placeholder("Captcha", exact=True)

    @property
    def _characters(self) -> Locator:
        # Why CSS: the characters are bare spans in a styled box (no role, label or test id),
        # `abha-patient-registration.component.html:101-112`.
        return self.page.locator(".captcha-box span")
