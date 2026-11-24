"""What the web app shows when the browser loses its connection (J35 DS-01..DS-03, DS-26).

The app listens only to the window `online`/`offline` events (`ng-connection-service` 1.0.4), which
`BrowserContext.set_offline` fires, so the context switch is the user pulling the cable.
Sources: overlay `app.component.ts:29-35`, `:141-158` (enabled when isElectron 0 and isAzure 1, `:108`);
header icon `homeLayout.component.html:487-498`. DRAFT: locators from the Angular source, not seen live.
"""

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage

OVERLAY_TITLE = "No internet connection found."
OVERLAY_HINT = "Check your connection or try again."
OVERLAY_TIMEOUT_MS = 10_000
# Why CSS: the no-wifi header icon is a bare svg in a div with no name, title or role; its viewBox is the
# only thing that tells it apart from the other header icons (homeLayout.component.html:487-498).
NO_WIFI_ICON = 'div.icn svg[viewBox="0 0 365.892 365.892"]'


class Connectivity:
    """The browser's network for one page's context."""

    def __init__(self, page: Page) -> None:
        self._page = page

    def go_offline(self) -> None:
        self._page.context.set_offline(True)

    def go_online(self) -> None:
        self._page.context.set_offline(False)


class NoInternetOverlay(BasePage):
    """The full-screen "No internet connection found." layer the root component puts over every route."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.title = page.get_by_text(OVERLAY_TITLE, exact=True)
        self.hint = page.get_by_text(OVERLAY_HINT, exact=True)

    def expect_shown(self) -> None:
        expect(self.title).to_be_visible(timeout=OVERLAY_TIMEOUT_MS)
        expect(self.hint).to_be_visible()

    def expect_gone(self) -> None:
        expect(self.title).to_be_hidden(timeout=OVERLAY_TIMEOUT_MS)


class HeaderConnectionIcon(BasePage):
    """The no-wifi icon the layout header shows while the browser is offline."""

    @property
    def no_wifi_icon(self) -> Locator:
        return self.page.locator(NO_WIFI_ICON)

    def expect_offline_icon(self) -> None:
        expect(self.no_wifi_icon).to_be_visible(timeout=OVERLAY_TIMEOUT_MS)


class PageIdentity:
    """Tells whether the browser reloaded the document: a mark set on `window` survives only without one."""

    MARK = "__qa_same_document"

    def __init__(self, page: Page) -> None:
        self._page = page

    def mark(self) -> None:
        self._page.evaluate(f"() => {{ window.{self.MARK} = true; }}")

    def is_same_document(self) -> bool:
        return bool(self._page.evaluate(f"() => window.{self.MARK} === true"))
