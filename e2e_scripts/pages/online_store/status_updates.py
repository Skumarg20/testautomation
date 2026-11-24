"""Counts the real `OnlineStore/StatusUpdationOfOnlineStore` calls the sale bill makes (OS-22).

The bill marks the order Converted only on its first final save: not on a temp-save, not on a resave
(`processout.transaction.component.ts:11986-11988, 22088-22106`). The calls go to the server (they only touch
this test's own seeded order); this class only listens.
"""

from playwright.sync_api import Page, Request
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.online_store.store_endpoints import STATUS_UPDATE

QUIET_WINDOW_MS = 3_000


class StatusUpdateCalls:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._seen: list[str] = []
        page.on("request", self._note)

    def count_once_settled(self) -> int:
        """How many calls were made, counted once none came for a quiet window."""
        while self._another_call_comes():
            continue
        return len(self._seen)

    def _another_call_comes(self) -> bool:
        try:
            with self._page.expect_request(STATUS_UPDATE, timeout=QUIET_WINDOW_MS):
                pass
        except PlaywrightTimeoutError:
            return False
        return True

    def _note(self, request: Request) -> None:
        if STATUS_UPDATE.search(request.url):
            self._seen.append(request.url)
