"""Records the requests a page starts to one kind of endpoint, so a test can prove nothing was sent.

Playwright emits `request` even for a request the offline context then fails, so an empty log means the
app never tried. Service workers are blocked for every context (root conftest), so none is hidden.
"""

from re import Pattern

from playwright.sync_api import Page, Request


class RequestLog:
    def __init__(self, page: Page, endpoint: Pattern[str]) -> None:
        self._endpoint = endpoint
        self._urls: list[str] = []
        page.on("request", self._record)

    @property
    def urls(self) -> tuple[str, ...]:
        return tuple(self._urls)

    def forget_earlier(self) -> None:
        """Starts the log afresh from this moment."""
        self._urls.clear()

    def _record(self, request: Request) -> None:
        if self._endpoint.search(request.url):
            self._urls.append(request.url)
