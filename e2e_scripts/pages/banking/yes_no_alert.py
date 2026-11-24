"""The app's Yes/No alert (delete, create cheque book). Its buttons are both labelled "Close" for screen
readers, so they are found by id."""

from playwright.sync_api import Locator

from pages.accounting.confirmation import Confirmation
from pages.base_page import BasePage


class YesNoAlert(BasePage):
    def is_shown(self, timeout_ms: int) -> bool:
        return Confirmation(self.page).is_asked(timeout_ms)

    def answer_yes(self) -> None:
        self._button("btnYes").click()

    def answer_no(self) -> None:
        self._button("btnNo").click()

    def _button(self, button_id: str) -> Locator:
        # Why ids: the buttons have aria-label "Close" and no test id (specs/item-master-crud.md).
        return Confirmation(self.page).question.locator(f"#{button_id}")
