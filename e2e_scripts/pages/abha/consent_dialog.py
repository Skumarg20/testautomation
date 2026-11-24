"""The ABHA consent popup that opens once 12 Aadhaar digits are typed (`abha-patient-consent.component.html`).

Seven declarations, all ticked by default (`.ts:44-50`), and an "I, [name]" box. "I Agree" with everything
filled asks the registration screen to request an OTP, so tests only press it when the OTP call is stubbed.
"""

from collections.abc import Callable
from re import Pattern

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.stubbed_endpoint import StubReply
from pages.masters.master_toasts import MasterToasts

DECLARATION_COUNT = 7
DIALOG_TIMEOUT_MS = 10_000

# A test step that gives the consent with fake values, the OTP request answered with the given reply.
GiveConsent = Callable[[StubReply], None]


class ConsentDialog(BasePage):
    def expect_shown_with_every_declaration_ticked(self) -> None:
        expect(self._declarations).to_have_count(DECLARATION_COUNT, timeout=DIALOG_TIMEOUT_MS)
        for declaration in self._declarations.all():
            expect(declaration).to_be_checked()

    def expect_name_box_shown(self) -> None:
        expect(self._name).to_be_visible()

    def untick_first_declaration(self) -> None:
        self._declarations.first.uncheck()

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def agree(self) -> None:
        self._dialog.get_by_role("button", name="I Agree").click()

    def close(self) -> None:
        self._dialog.get_by_role("button", name="Close").click()

    def expect_refused_with(self, message: Pattern[str]) -> None:
        MasterToasts(self.page).expect_warning_saying(message)
        expect(self._dialog).to_be_visible()

    def expect_name_focused(self) -> None:
        expect(self._name).to_be_focused()

    def expect_closed(self) -> None:
        expect(self._dialog).to_be_hidden(timeout=DIALOG_TIMEOUT_MS)

    @property
    def _dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text="I hereby declare that")

    @property
    def _declarations(self) -> Locator:
        return self._dialog.get_by_role("checkbox")

    @property
    def _name(self) -> Locator:
        # The name box is the dialog's only text box; it has no label of its own (".html: #nameInput").
        return self._dialog.get_by_role("textbox")
