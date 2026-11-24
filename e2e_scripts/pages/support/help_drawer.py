"""The Help drawer the header "Help" icon slides in (`homeLayout.component.html:841-842`, `:3085-3260`;
`homelayout.component.ts:1379-1407`, `:2681-2687`, `:3986-4002`). Locators from the Angular source, not yet
checked live.

The drawer is always in the DOM; opening it moves it into view (`right: 0`) and closing moves it out
(`right: -103%`), so "open" is asserted with `to_be_in_viewport`, not with visibility.
"""

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage

DRAWER_TIMEOUT_MS = 15_000
HELP_HEADING = "Help ?"
BANNER = "We're here to help you any time."
SECTION_LABELS = ("Contact info", "Help topics", "Support", "Learn", "Follow us")
SUPPORT_EMAIL = "support@margbooks.com"
# `copyText` shows the tick for 2 s, then the copy icon again (`homelayout.component.ts:3994-4002`).
COPIED_TICK_TIMEOUT_MS = 5_000


class HelpDrawer(BasePage):
    def open(self) -> None:
        self.page.get_by_title("Help", exact=True).click()
        self.expect_open()

    def expect_open(self) -> None:
        expect(self._heading).to_be_in_viewport(timeout=DRAWER_TIMEOUT_MS)

    def expect_closed(self) -> None:
        expect(self._heading).not_to_be_in_viewport(timeout=DRAWER_TIMEOUT_MS)

    def expect_banner(self) -> None:
        expect(self._drawer).to_contain_text("24x7 support")
        expect(self._drawer).to_contain_text(BANNER)

    def expect_sections(self) -> None:
        for label in SECTION_LABELS:
            expect(self._drawer.get_by_text(label, exact=True).first).to_be_visible()

    def expect_contacts(self, contacts: tuple[str, ...]) -> None:
        for contact in contacts:
            expect(self._drawer.get_by_role("link", name=contact, exact=True)).to_be_visible()

    def copy_support_email(self) -> str:
        """Copies the support address with its button and returns what the clipboard then holds. The page's
        context must have clipboard permissions."""
        self._copy_button.click()
        clipboard: str = self.page.evaluate("navigator.clipboard.readText()")
        return clipboard

    def expect_copied_tick(self) -> None:
        expect(self._copy_button.locator(".copy-message")).to_be_visible(timeout=COPIED_TICK_TIMEOUT_MS)

    def expect_copy_icon_back(self) -> None:
        """The tick is gone and the plain copy icon is back (`homeLayout.component.html:3130-3139`)."""
        expect(self._copy_button.locator(".copy-message")).to_have_count(0, timeout=COPIED_TICK_TIMEOUT_MS)
        expect(self._copy_button.locator("span.copied-icon")).to_be_visible()

    def chat_now(self) -> None:
        """Asks the Zoho SalesIQ widget to show its float window (`homelayout.component.ts:4004-4010`)."""
        self._drawer.get_by_role("link", name="Chat Now").click()

    def raise_ticket(self) -> None:
        self._drawer.get_by_role("link", name="Raise ticket").click()

    def visit_portal(self) -> Page:
        """The tab "Visit portal" opens (`window.open`)."""
        with self.page.expect_popup() as popup:
            self._drawer.get_by_role("link", name="Visit portal").click()
        return popup.value

    @property
    def _heading(self) -> Locator:
        return self.page.get_by_role("heading", name=HELP_HEADING, exact=True)

    @property
    def _copy_button(self) -> Locator:
        return self._drawer.get_by_role("button", name="Copy email address")

    @property
    def _drawer(self) -> Locator:
        # Why CSS: the drawer is a plain div with no role, label or test id.
        return self.page.locator(".helpPanel .help-window")
