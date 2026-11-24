"""The "Alert!" dialog with a single OK button, e.g. "1200 Cr Adjusted in Vch No. 0000022" when an adjusted
sale bill is opened for change (live 2026-10-09)."""

import re
from re import Pattern

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

TITLE = "Alert!"
OK = re.compile(r"^\s*OK\s*$")
DIALOG_TIMEOUT_MS = 15_000


class InfoAlert(BasePage):
    def acknowledge_if_shown(self, timeout_ms: int) -> None:
        if appears_within(self._dialog, timeout_ms):
            self.acknowledge()

    def acknowledge(self) -> None:
        # Its OK button is named "Close" for assistive tech (like Yes/No in ConfirmDialog), so match the text.
        self._dialog.get_by_role("button").filter(has_text=OK).first.click()
        expect(self._dialog).to_be_hidden(timeout=DIALOG_TIMEOUT_MS)

    def expect_saying(self, message: Pattern[str]) -> None:
        expect(self._dialog.filter(has_text=message)).to_be_visible(timeout=DIALOG_TIMEOUT_MS)

    @property
    def _dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has=self.page.get_by_text(TITLE, exact=True))
