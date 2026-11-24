"""The "Confirmation" dialog ("Are you sure you want to delete the selected Record?").

Its Yes and No buttons both carry the accessible name "Close", so they are told apart by their text.
"""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

YES = re.compile(r"^\s*Yes\s*$")
NO = re.compile(r"^\s*No\s*$")
DIALOG_TIMEOUT_MS = 15_000


class ConfirmDialog(BasePage):
    def answer_yes(self) -> None:
        self._answer(YES)

    def answer_no(self) -> None:
        self._answer(NO)

    def expect_asking(self, question: str) -> None:
        expect(self._dialog).to_contain_text(question, timeout=DIALOG_TIMEOUT_MS)

    def _answer(self, answer: re.Pattern[str]) -> None:
        button = self._dialog.get_by_role("button").filter(has_text=answer).first
        expect(button).to_be_visible(timeout=DIALOG_TIMEOUT_MS)
        button.click()
        expect(self._dialog).to_be_hidden(timeout=DIALOG_TIMEOUT_MS)

    @property
    def _dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name="Confirmation", exact=True)
        )
