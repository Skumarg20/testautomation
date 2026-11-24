"""Counts the API calls (XHR / fetch) a screen makes while a block of steps runs."""

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from playwright.sync_api import Page, Request

API_RESOURCE_TYPES = frozenset({"xhr", "fetch"})


@dataclass
class RequestLog:
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def record(self, request: Request) -> None:
        if request.resource_type in API_RESOURCE_TYPES:
            self.calls.append((request.method, request.url, request.post_data or ""))

    def count_url_containing(self, fragment: str) -> int:
        needle = fragment.lower()
        return sum(1 for _, url, _ in self.calls if needle in url.lower())

    def repeated_calls(self) -> dict[tuple[str, str, str], int]:
        """Calls made more than once with the same method, address and body."""
        return {call: times for call, times in Counter(self.calls).items() if times > 1}


@contextmanager
def logging_requests(page: Page) -> Iterator[RequestLog]:
    log = RequestLog()
    page.on("request", log.record)
    try:
        yield log
    finally:
        page.remove_listener("request", log.record)
