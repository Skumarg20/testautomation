"""margmart.com's vendor registration, which the create-store page opens in a new tab (OS-07).

The tab is answered by a blank stand-in page, so nothing reaches margmart.com. The stand-in is a context route
(a page route would not cover the new tab) registered after the `SendGuard`, so it runs before the guard:
Playwright runs matching routes in the opposite order of registration.
"""

from collections.abc import Callable

from playwright.sync_api import Page, Route

from pages.online_store.store_endpoints import MARG_MART_PORTAL

TAB_TIMEOUT_MS = 60_000
STAND_IN_PAGE = "<!doctype html><title>margmart.com stand-in</title>"


class MargMartPortalStub:
    def __init__(self, page: Page) -> None:
        self._page = page

    def answer(self) -> None:
        self._page.context.route(MARG_MART_PORTAL, self._stand_in)

    def url_opened_by(self, action: Callable[[], object]) -> str:
        """Runs `action` and answers the URL of the tab it opened (fragment included)."""
        with self._page.context.expect_page(timeout=TAB_TIMEOUT_MS) as opened:
            action()
        tab = opened.value
        tab.wait_for_url(MARG_MART_PORTAL, timeout=TAB_TIMEOUT_MS)
        return tab.url

    @staticmethod
    def _stand_in(route: Route) -> None:
        route.fulfill(status=200, content_type="text/html", body=STAND_IN_PAGE)
