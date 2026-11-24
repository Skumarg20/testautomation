"""A safety net for the communication screens: no save and no message may leave the browser.

The Email, SMS and Transaction SMS screens hold the tenant's communication setup, and some buttons
dispatch real messages. The guard aborts every non-GET request whose path looks like a save or a
dispatch, on any host (a localhost or other non-production target included) and from every tab of the
test's browser context, remembers it, and lets the test fail on it.
"""

import re
from urllib.parse import urlsplit

from playwright.sync_api import Page, Route

SAVE_OR_DISPATCH = re.compile(
    r"("
    r"template/save|template/updatestatus|emailpreference|emailtoken|"
    r"whatsapp|templateinfo|dlt|send|sms"
    r")",
    re.IGNORECASE,
)


class OutboundRequestAttemptedError(AssertionError):
    def __init__(self, requests: list[str]) -> None:
        super().__init__(f"The screen tried to save or send (aborted by the guard): {requests}")


class OutboundGuard:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._aborted: list[str] = []

    def arm(self) -> None:
        self._page.context.route(_is_save_or_dispatch, self._intercept)

    def expect_nothing_sent(self) -> None:
        if self._aborted:
            raise OutboundRequestAttemptedError(self._aborted)

    def _intercept(self, route: Route) -> None:
        request = route.request
        if request.method == "GET":
            route.fallback()
            return
        self._aborted.append(f"{request.method} {request.url}")
        route.abort()


def _is_save_or_dispatch(url: str) -> bool:
    """Matches everything after the host, whatever the host is: the allowed targets include localhost."""
    parts = urlsplit(url)
    return SAVE_OR_DISPATCH.search(f"{parts.path}?{parts.query}") is not None
