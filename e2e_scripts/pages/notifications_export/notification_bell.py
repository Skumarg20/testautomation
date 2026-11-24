"""The header bell (live 2026-10-12): link "<count> Notification" (title "Notifications"); its dropdown has
the tabs "Notification <n>" and "Announcement <n>" and up to four items per tab."""

import re

from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.accounting.confirmation import Confirmation
from pages.banking.yes_no_alert import YesNoAlert
from pages.base_page import BasePage

BELL_TIMEOUT_MS = 30_000
BELL_NAME = re.compile(r"^(\d+ )?Notification$")
NOTIFICATIONS_TAB = re.compile(r"^Notification\b")
ANNOUNCEMENTS_TAB = re.compile(r"^Announcement\b")
EMPTY_HEADING = "No notifications yet"
EMPTY_TEXT = "You're all caught up!"
NO_ANNOUNCEMENT = "No announcement!"
VIEW_ALL_ANNOUNCEMENTS = "View All Announcements"
DESKTOP_NOTIFICATION_LABEL = re.compile(r"Desktop Notification (Enable|Disable)")
INJECTED_FLAG_SCRIPT = "() => window.qaInjected === true"
INJECTION_WAIT_MS = 5_000


class NotificationBell(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._bell = page.get_by_role("link", name=BELL_NAME)

    def expect_shown(self) -> None:
        expect(self._bell).to_be_visible(timeout=BELL_TIMEOUT_MS)
        expect(self._bell).to_have_attribute("title", "Notifications")

    def expect_badge(self, count: int) -> None:
        """The badge is part of the link's name: "4 Notification"."""
        expect(self._bell).to_have_accessible_name(f"{count} Notification", timeout=BELL_TIMEOUT_MS)

    def expect_no_badge(self) -> None:
        expect(self._bell).to_have_accessible_name("Notification", timeout=BELL_TIMEOUT_MS)

    def open(self) -> None:
        self._bell.click()
        expect(self._tab(NOTIFICATIONS_TAB)).to_be_visible(timeout=BELL_TIMEOUT_MS)

    def close(self) -> None:
        self._bell.click()
        expect(self._tab(NOTIFICATIONS_TAB)).to_be_hidden(timeout=BELL_TIMEOUT_MS)

    def expect_tab_badges(self, notifications: int, announcements: int) -> None:
        expect(self._tab(NOTIFICATIONS_TAB)).to_have_accessible_name(f"Notification {notifications}")
        expect(self._tab(ANNOUNCEMENTS_TAB)).to_have_accessible_name(f"Announcement {announcements}")

    def show_announcements(self) -> None:
        self._tab(ANNOUNCEMENTS_TAB).click()

    def listed_items(self, prefix: str) -> Locator:
        """The dropdown entries whose title starts with `prefix` (each entry is a link)."""
        return self.page.get_by_role("link", name=re.compile(rf"^{re.escape(prefix)} \d+\b"))

    def item(self, name: str) -> Locator:
        return self.page.get_by_role("link", name=re.compile(rf"^{re.escape(name)}\b"))

    def open_link_item(self, name: str) -> Page:
        """Clicks a link item (`isLink` 1, target _blank) and returns the tab it opened."""
        with self.page.context.expect_page(timeout=BELL_TIMEOUT_MS) as new_tab:
            self.item(name).click()
        return new_tab.value

    def expect_empty_state(self) -> None:
        expect(self.page.get_by_role("heading", name=EMPTY_HEADING)).to_be_visible(timeout=BELL_TIMEOUT_MS)
        expect(self.page.get_by_text(EMPTY_TEXT)).to_be_visible()

    def expect_no_announcement_message(self) -> None:
        expect(self.page.get_by_text(NO_ANNOUNCEMENT)).to_be_visible(timeout=BELL_TIMEOUT_MS)

    def view_all_announcements(self) -> Locator:
        return self.page.get_by_text(VIEW_ALL_ANNOUNCEMENTS)

    def desktop_notification_label(self) -> str:
        return self.page.get_by_text(DESKTOP_NOTIFICATION_LABEL).inner_text().strip()

    def toggle_desktop_notification(self) -> None:
        """The app reacts to a window click whose target id is the icon's id, so the click is dispatched
        on the svg itself; a mouse click lands on a <path> inside it and the app ignores it.
        Why ids: the two icons are bare svgs with no role or name."""
        self.page.locator("#btnEnableNotification, #btnDisableNotification").dispatch_event("click")

    def expect_toggle_question(self, question: re.Pattern[str]) -> None:
        expect(Confirmation(self.page).question).to_contain_text(question, timeout=BELL_TIMEOUT_MS)

    def decline_toggle(self) -> None:
        YesNoAlert(self.page).answer_no()
        expect(Confirmation(self.page).question).to_be_hidden(timeout=BELL_TIMEOUT_MS)

    def injected_script_ran(self) -> bool:
        """True if markup in a description ran script (it sets window.qaInjected) within a few seconds."""
        try:
            self.page.wait_for_function(INJECTED_FLAG_SCRIPT, timeout=INJECTION_WAIT_MS)
        except PlaywrightTimeoutError:
            return False
        return True

    def _tab(self, name: re.Pattern[str]) -> Locator:
        return self.page.get_by_role("tab", name=name)
