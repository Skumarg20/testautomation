"""Safety net for screens that can reach a real person or a live outside system: a send, an OTP, a write to
Marg's support desk, a tenant-wide save.

Each journey names the endpoints it must never let through (for example
`pages/notifications_export/delivery_endpoints.py`, `pages/support/desk_endpoints.py`). A request to any of
them is aborted before it reaches the server and remembered, so the test fails loudly in teardown.

The guard is a context route, so it covers every tab of the test's browser context, and a page route (a
stub that answers the call itself) takes precedence over it: what a stub answers never meets the guard,
and what no stub answers is aborted. Routing only sees the app's API calls because every context blocks
the app's service worker (`browser_context_args` in the root conftest).
"""

from re import Pattern

from playwright.sync_api import Page, Route


class SendAttemptedError(AssertionError):
    def __init__(self, requests: list[str]) -> None:
        super().__init__(
            f"The screen tried to send or write to a live system (aborted by the guard): {requests}"
        )


class SendGuard:
    def __init__(self, page: Page, endpoints: Pattern[str]) -> None:
        self._page = page
        self._endpoints = endpoints
        self._aborted: list[str] = []

    def arm(self) -> None:
        """Call before the page's first navigation. Guards every tab of the page's browser context, so a
        tab the app opens (a link, a PDF) is covered too."""
        self._page.context.route(self._endpoints, self._abort)

    def expect_nothing_sent(self) -> None:
        if self._aborted:
            raise SendAttemptedError(self._aborted)

    def _abort(self, route: Route) -> None:
        self._aborted.append(f"{route.request.method} {route.request.url}")
        route.abort()
