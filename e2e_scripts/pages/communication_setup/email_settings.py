"""Control Room > Email Settings: the email template list per transaction type and Email Preference."""

from playwright.sync_api import Locator, expect

from pages.communication_setup.communication_settings import SECTION_TIMEOUT_MS, CommunicationSettings
from pages.communication_setup.email_template_form import EmailTemplateForm

DEFAULT_TEMPLATE_LABEL = "Default Template"


class EmailSettings(CommunicationSettings):
    def open(self) -> None:
        self.open_section("Email Settings")

    def expect_types_listed(self, types: tuple[str, ...]) -> None:
        for template_type in types:
            expect(self._type_link(template_type)).to_be_visible(timeout=SECTION_TIMEOUT_MS)

    def choose_type(self, template_type: str) -> None:
        self._type_link(template_type).click()
        expect(self.main.get_by_role("heading", name=template_type, level=4)).to_be_visible()

    def expect_default_template(self, name: str, subject: str) -> None:
        row = self._default_row()
        expect(row).to_contain_text(name)
        expect(row).to_contain_text(subject)

    def expect_template_not_listed(self, name: str) -> None:
        expect(self._templates.get_by_role("row").filter(has_text=name)).to_have_count(0)

    def start_new_template(self) -> EmailTemplateForm:
        self.main.get_by_role("button", name="+ New").click()
        return EmailTemplateForm(self.page).expect_open()

    def clone_default_template(self) -> EmailTemplateForm:
        self._default_row().get_by_role("link", name="Clone").click()
        return EmailTemplateForm(self.page).expect_open()

    def expect_default_sender(self, address: str) -> None:
        sender = self._templates.get_by_role("row").filter(has_text=address)
        expect(sender).to_contain_text("System Verified")
        expect(sender).to_contain_text("Default")

    @property
    def _templates(self) -> Locator:
        return self.main.get_by_role("table")

    def _type_link(self, template_type: str) -> Locator:
        # The template table can hold a link of the same name (a template is named after its type);
        # the type list comes first on the page.
        return self.main.get_by_role("link", name=template_type, exact=True).first

    def _default_row(self) -> Locator:
        return self._templates.get_by_role("row").filter(has_text=DEFAULT_TEMPLATE_LABEL)
