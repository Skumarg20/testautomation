"""The Yes/No alert of the item master: "add item Opening?" after a save and "delete the selected Record?"."""

from playwright.sync_api import Locator, expect

from pages.accounting.confirmation import Confirmation

ALERT_TIMEOUT_MS = 30_000


class ItemAlert(Confirmation):
    def expect_asking(self, question: str) -> None:
        expect(self.question).to_contain_text(question, timeout=ALERT_TIMEOUT_MS)

    def answer_yes(self) -> None:
        self._button("btnYes").click()
        expect(self.question).to_be_hidden()

    def answer_no(self) -> None:
        self._button("btnNo").click()
        expect(self.question).to_be_hidden()

    def _button(self, button_id: str) -> Locator:
        # Why an id: both buttons carry aria-label="Close", so their accessible names are not Yes and No.
        return self.question.locator(f"#{button_id}")
