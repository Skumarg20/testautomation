"""Control Room > Transaction SMS: the WhatsApp / SMS sending channel and the message preview per type.

The channel buttons change how the tenant sends messages or link a device, so tests only look at them.
"""

import re

from playwright.sync_api import Locator, expect

from pages.communication_setup.communication_settings import SECTION_TIMEOUT_MS, CommunicationSettings

SENDING_CHANNELS = (
    "Send Via MargBooks",
    "Send Via Whatsapp Web",
    "Integrate Your Own WhatsApp Businees Number",
)
ANY_TEXT = re.compile(r"\S")


class TransactionMessages(CommunicationSettings):
    def open(self) -> None:
        self.open_section("Transaction SMS")
        expect(self._transaction_type).to_be_visible(timeout=SECTION_TIMEOUT_MS)

    def expect_sending_channels(self) -> None:
        for channel in SENDING_CHANNELS:
            expect(self.main.get_by_role("button", name=channel)).to_be_visible()

    def expect_transaction_types(self, types: tuple[str, ...]) -> None:
        expect(self._transaction_type.get_by_role("option")).to_have_text(list(types))

    def choose(self, transaction_type: str) -> None:
        self._transaction_type.select_option(transaction_type)

    def expect_preview_containing(self, text: str) -> None:
        expect(self._preview).to_contain_text(text)

    def expect_preview_shows_a_message(self) -> None:
        expect(self._preview).to_have_text(ANY_TEXT)

    @property
    def _transaction_type(self) -> Locator:
        return self.main.get_by_role("combobox")

    @property
    def _preview(self) -> Locator:
        # Why CSS: the preview is a bare <pre> under "Message Preview" with no role, label or id.
        return self.main.locator("pre")
