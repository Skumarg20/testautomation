"""What a sale bill tells the user: warning toasts and the "Confirmation" question."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog

WARNING_TIMEOUT_MS = 15_000
ABSENCE_WINDOW_MS = 3_000


class UnexpectedMessageError(AssertionError):
    def __init__(self, text: str) -> None:
        super().__init__(f'The bill showed "{text}", which it must not show with this setting')


class BillMessages(BasePage):
    def expect_warning(self, text: str) -> None:
        expect(self._warning_with(text).first).to_be_visible(timeout=WARNING_TIMEOUT_MS)

    def expect_warning_like(self, pattern: re.Pattern[str]) -> None:
        expect(self._warning_with(pattern).first).to_be_visible(timeout=WARNING_TIMEOUT_MS)

    def expect_any_notification(self) -> None:
        """A toast of any kind, for a refusal whose wording the web source does not hold (server errors)."""
        expect(self.page.locator("notifier-notification").first).to_be_visible(timeout=WARNING_TIMEOUT_MS)

    def expect_no_warning(self, text: str) -> None:
        if appears_within(self._warning_with(text), ABSENCE_WINDOW_MS):
            raise UnexpectedMessageError(text)

    def expect_question(self, text: str) -> None:
        ConfirmDialog(self.page).expect_asking(text)

    def expect_no_question(self, text: str) -> None:
        if appears_within(self._question_with(text), ABSENCE_WINDOW_MS):
            raise UnexpectedMessageError(text)

    def answer_no(self) -> None:
        ConfirmDialog(self.page).answer_no()

    def answer_yes(self) -> None:
        ConfirmDialog(self.page).answer_yes()

    def _warning_with(self, text: str | re.Pattern[str]) -> Locator:
        # Why CSS: the notifier library has no role or test id (same locator as pages/accounting/toasts.py).
        toasts = self.page.locator("notifier-notification.notifier__notification--warning")
        return toasts.filter(has_text=text)

    def _question_with(self, text: str) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text=text)
