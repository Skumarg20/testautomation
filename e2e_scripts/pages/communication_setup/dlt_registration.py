"""Control Room > SMS Settings > "Configure DLT Registration": the DLT number and sender id popup."""

from dataclasses import dataclass

from playwright.sync_api import Locator, expect

from pages.communication_setup.communication_settings import SECTION_TIMEOUT_MS, CommunicationSettings


@dataclass(frozen=True)
class DltDetails:
    registered_number: str
    sender_id: str


class DltRegistration(CommunicationSettings):
    def open(self) -> None:
        self.open_section("SMS Settings")
        self.main.get_by_role("button", name="Configure DLT Registration").click()
        expect(self._registered_number).to_be_visible(timeout=SECTION_TIMEOUT_MS)

    def current_details(self) -> DltDetails:
        return DltDetails(self._registered_number.input_value(), self._sender_id.input_value())

    def enter(self, details: DltDetails) -> None:
        self._registered_number.fill(details.registered_number)
        self._sender_id.fill(details.sender_id)

    def cancel(self) -> None:
        self.page.get_by_role("button", name="Cancel", exact=True).click()
        expect(self._registered_number).to_be_hidden()

    def expect_details(self, details: DltDetails) -> None:
        expect(self._registered_number).to_have_value(details.registered_number)
        expect(self._sender_id).to_have_value(details.sender_id)

    @property
    def _registered_number(self) -> Locator:
        # The popup's two inputs have no label, id or name; they are the only textboxes in SMS Settings
        # (the section search is a searchbox), in the order Registered Number, Sender ID.
        return self.main.get_by_role("textbox").nth(0)

    @property
    def _sender_id(self) -> Locator:
        return self.main.get_by_role("textbox").nth(1)
