"""The "are you sure?" dialog that the app raises for unsaved changes and deletes."""

from playwright.sync_api import Locator

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

DEFAULT_LOOKUP_MS = 2_000


class Confirmation(BasePage):
    @property
    def question(self) -> Locator:
        # Why CSS: the dialog is a bare div with classes only.
        return self.page.locator("div.active.modal-new")

    def is_asked(self, timeout_ms: int = DEFAULT_LOOKUP_MS) -> bool:
        return appears_within(self.question, timeout_ms)

    def answer_yes(self) -> None:
        # Why an id: Yes and No both carry aria-label="Close", so their accessible names are not Yes and No.
        self.question.locator("#btnYes").click()

    def answer_yes_if_asked(self, timeout_ms: int = DEFAULT_LOOKUP_MS) -> None:
        if self.is_asked(timeout_ms):
            self.answer_yes()
