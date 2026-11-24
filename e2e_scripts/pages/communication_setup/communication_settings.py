"""The Control Room page and its left-hand sections (Email Settings, SMS Settings, Transaction SMS)."""

from typing import Literal

from playwright.sync_api import Locator, expect

from pages.settings.control_room import ControlRoom

CommunicationSection = Literal["Email Settings", "SMS Settings", "Transaction SMS"]
SECTION_TIMEOUT_MS = 60_000
CONTROL_ROOM_PATH = "/mstr/margsetup-controlroom"
PAGE_LOAD_TIMEOUT_MS = 150_000


class CommunicationSettings(ControlRoom):
    def open_section(self, section: CommunicationSection) -> None:
        """Opens the Control Room by its URL: the Settings icon path is slow to bind right after a page
        load on the QA host (clicks were lost); `expect_sections_listed` keeps the menu path covered."""
        self.page.goto(CONTROL_ROOM_PATH, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        expect(self._control_room_heading).to_be_visible(timeout=PAGE_LOAD_TIMEOUT_MS)
        self._section_entry(section).click(timeout=SECTION_TIMEOUT_MS)
        expect(self.main.get_by_role("heading", name=section, level=2)).to_be_visible(
            timeout=SECTION_TIMEOUT_MS
        )

    def expect_sections_listed(self, sections: tuple[CommunicationSection, ...]) -> None:
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        expect(self._control_room_heading).to_be_visible(timeout=SECTION_TIMEOUT_MS)
        for section in sections:
            expect(self._section_entry(section)).to_be_visible(timeout=SECTION_TIMEOUT_MS)

    @property
    def main(self) -> Locator:
        return self.page.get_by_role("main")

    @property
    def _control_room_heading(self) -> Locator:
        return self.main.get_by_role("heading", name="Control Room", level=1)

    def _section_entry(self, section: CommunicationSection) -> Locator:
        # The entries are list items without a link role, so they are found by their whole text.
        return self.main.get_by_role("listitem").get_by_text(section, exact=True)
