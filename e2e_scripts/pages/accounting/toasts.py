"""The notifier toasts at the top of the app: success, warning and their dismiss button."""

from re import Pattern

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

WARNING_TIMEOUT_MS = 15_000
SUCCESS_TIMEOUT_MS = 50_000
DISMISS_LOOKUP_MS = 2_000
HIDDEN_TIMEOUT_MS = 10_000


class Toasts(BasePage):
    def warning_appears(self, timeout_ms: int) -> bool:
        return appears_within(self._toast("warning"), timeout_ms)

    def expect_warning(self) -> None:
        self._expect_and_dismiss("warning", WARNING_TIMEOUT_MS)

    def expect_success(self, timeout_ms: int = SUCCESS_TIMEOUT_MS) -> None:
        self._expect_and_dismiss("success", timeout_ms)

    def expect_success_saying(self, message: Pattern[str], timeout_ms: int = SUCCESS_TIMEOUT_MS) -> None:
        expect(self._toast("success")).to_contain_text(message, timeout=timeout_ms)
        self._dismiss()

    def expect_any_saying(self, message: Pattern[str], timeout_ms: int = WARNING_TIMEOUT_MS) -> None:
        """A toast of any kind with this text; for refusals whose kind (warning or error) is not the point."""
        toast = self.page.locator("notifier-notification").filter(has_text=message).first
        expect(toast).to_be_visible(timeout=timeout_ms)

    def expect_warning_stays_visible(self) -> None:
        expect(self._toast("warning")).to_be_visible(timeout=WARNING_TIMEOUT_MS)

    def _toast(self, kind: str) -> Locator:
        # Why CSS: the notifier library exposes no role or test id (same locator as pages/signup_page.py).
        return self.page.locator(f"notifier-notification.notifier__notification--{kind}").first

    def _expect_and_dismiss(self, kind: str, timeout_ms: int) -> None:
        toast = self._toast(kind)
        expect(toast).to_be_visible(timeout=timeout_ms)
        self._dismiss()
        expect(toast).to_be_hidden(timeout=HIDDEN_TIMEOUT_MS)

    def _dismiss(self) -> None:
        close = self.page.get_by_title("dismiss")
        if not appears_within(close, DISMISS_LOOKUP_MS):
            return
        try:
            close.first.click(timeout=DISMISS_LOOKUP_MS)
        except PlaywrightTimeoutError:
            # A toast covered by a backdrop cannot be clicked; it still closes by itself and the
            # caller asserts that it is hidden.
            return
