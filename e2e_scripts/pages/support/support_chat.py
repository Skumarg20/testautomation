"""The "Support Chat" modal (`support-chat.component.html`, `support-chat.component.ts`). Locators from the
Angular source, not yet checked live. The list page holds a hidden copy of the same markup (`d-none`,
`support-ticket.component.html:249-320`), so everything is looked up inside the dialog.
"""

import re

from playwright.sync_api import Locator, Page, expect

CHAT_TIMEOUT_MS = 30_000
MESSAGE_PLACEHOLDER = "Type your message"


class SupportChat:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._dialog = page.get_by_role("dialog").filter(has_text=re.compile(r"Ticket ID\s*:"))

    def expect_open_for(self, ticket_id: int) -> None:
        expect(self._dialog).to_contain_text(
            re.compile(rf"Ticket ID\s*:\s*{ticket_id}"), timeout=CHAT_TIMEOUT_MS
        )

    def expect_message(self, text: str) -> None:
        expect(self._dialog.get_by_text(text)).to_be_visible(timeout=CHAT_TIMEOUT_MS)

    def expect_typing_disabled(self) -> None:
        expect(self._message_box).not_to_be_editable(timeout=CHAT_TIMEOUT_MS)

    def expect_typing_enabled(self) -> None:
        expect(self._message_box).to_be_editable(timeout=CHAT_TIMEOUT_MS)

    def send(self, message: str) -> None:
        """Enter sends (`keyup.enter`, `support-chat.component.html:41`)."""
        self._message_box.fill(message)
        self._message_box.press("Enter")

    def close_with_escape(self) -> None:
        self._page.keyboard.press("Escape")

    def expect_closed(self) -> None:
        expect(self._dialog).to_have_count(0, timeout=CHAT_TIMEOUT_MS)

    @property
    def _message_box(self) -> Locator:
        return self._dialog.get_by_placeholder(MESSAGE_PLACEHOLDER)
