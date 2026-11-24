"""The email template form that "+ New" and "Clone" open inside Control Room > Email Settings.

Tests only fill, validate and close it: saving a template cannot be undone from the UI (spec N1).
"""

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.communication_setup.communication_settings import SECTION_TIMEOUT_MS
from pages.communication_setup.email_messages import INVALID_EMAIL


class EmailTemplateForm(BasePage):
    def expect_open(self) -> "EmailTemplateForm":
        expect(self._name).to_be_visible(timeout=SECTION_TIMEOUT_MS)
        return self

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def enter_subject(self, subject: str) -> None:
        self._subject.fill(subject)

    def add_cc(self, address: str) -> None:
        self._cc.click()
        self._cc.press_sequentially(address)
        self._cc.press("Enter")

    def save(self) -> None:
        self.page.get_by_role("button", name="F10 Save").click()

    def close(self) -> None:
        self.page.get_by_role("button", name="Esc Close").click()
        expect(self._name).to_be_hidden()

    def expect_name_flagged_with(self, message: str) -> None:
        self._name_marker.hover()
        expect(self.page.get_by_role("tooltip").filter(has_text=message)).to_be_visible()

    def expect_name(self, name: str) -> None:
        expect(self._name).to_have_value(name)

    def expect_subject(self, subject: str) -> None:
        expect(self._subject).to_have_value(subject)

    def expect_not_set_as_default(self) -> None:
        expect(self.page.get_by_role("checkbox", name="Set as default")).not_to_be_checked()

    def expect_cc_refused(self, address: str) -> None:
        Toasts(self.page).expect_any_saying(INVALID_EMAIL)
        expect(self._cc).to_have_value("")
        expect(self.page.get_by_role("main").get_by_text(address)).to_have_count(0)

    @property
    def _name(self) -> Locator:
        # Why CSS: the form's labels are plain text not tied to the inputs; the ids are stable.
        return self.page.locator("#txttempname")

    @property
    def _subject(self) -> Locator:
        return self.page.locator("#txtsubject")  # Why CSS: as for the name

    @property
    def _cc(self) -> Locator:
        return self.page.locator("#chipListemailcc")  # Why CSS: as for the name

    @property
    def _name_marker(self) -> Locator:
        # The "!" markers come in form order (Name before Subject); the first one belongs to Name.
        return self.page.get_by_role("main").get_by_role("link", name="!").first
