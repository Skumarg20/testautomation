"""Report scheduler "Schedule Setup" (`/other/Schedular-process`, live 2026-10-12).

Report Type comes preset to "Inventory" (disabled) with the reports Minimum Stock and Maximum Stock, the
platform Email is preset and the frequency is Daily. "Schedule" validates on the client before
`WorkFlow/SchedulerSave`; the send guard aborts that call should validation ever let it through.
"""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage

PATH = "/other/Schedular-process"
TITLE = "Schedule Setup"
LOAD_TIMEOUT_MS = 60_000
TO_EMAIL_PLACEHOLDER = "Email (Separate emails with a comma)"


class ScheduleSetupPage(BasePage):
    def open(self) -> None:
        self.goto(PATH, LOAD_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=TITLE, level=1)).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def tick_report(self, report: str) -> None:
        self.page.get_by_role("listitem").filter(has_text=report).get_by_role("checkbox").check()

    def enter_to_email(self, address: str) -> None:
        # Two boxes share the placeholder (To and Cc); To comes first.
        self.page.get_by_role("textbox", name=TO_EMAIL_PLACEHOLDER).first.fill(address)

    def schedule(self) -> None:
        self.page.get_by_role("button", name="Schedule", exact=True).click()

    def expect_warning(self, message: str) -> None:
        # Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
        Toasts(self.page).expect_any_saying(re.compile(re.escape(message), re.IGNORECASE))

    @property
    def _name(self) -> Locator:
        # Why CSS: the name box has no label element, placeholder or test id; only its form control name.
        return self.page.locator('input[formcontrolname="SchedulerName"]')
