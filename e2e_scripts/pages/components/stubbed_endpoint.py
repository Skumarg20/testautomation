"""One API endpoint answered by the test instead of the server, with every request it answered kept.

A stub is a page route, so it takes precedence over the context-wide `SendGuard`: a write the test stubs is
answered here and never leaves the browser, a write nobody stubs is aborted by the guard. `capture_one`
proves the interception before a test may look at the screen: the response must come from this stub (not
from the server and not from a service worker), and the stub must have answered exactly one more request.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from re import Pattern
from typing import Any
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, Route
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

QUIET_WINDOW_MS = 1_500
CAPTURE_TIMEOUT_MS = 15_000


@dataclass(frozen=True)
class StubReply:
    payload: object
    status: int = 200


@dataclass(frozen=True)
class AnsweredRequest:
    method: str
    url: str
    post_data: str | None

    def json_body(self) -> dict[str, Any]:
        body: dict[str, Any] = json.loads(self.post_data or "{}")
        return body

    def query_value(self, name: str) -> str:
        return parse_qs(urlsplit(self.url).query)[name][0]


class InterceptionNotProvenError(AssertionError):
    def __init__(self, endpoint: Pattern[str], detail: str) -> None:
        super().__init__(f"The stub for {endpoint.pattern} did not answer the request: {detail}")


class UnexpectedRequestError(AssertionError):
    def __init__(self, endpoint: Pattern[str]) -> None:
        super().__init__(f"The screen called {endpoint.pattern}, which this step must not call")


class StubbedEndpoint:
    def __init__(self, page: Page, endpoint: Pattern[str]) -> None:
        self._page = page
        self._endpoint = endpoint
        self._reply = StubReply({})
        self._answered: list[AnsweredRequest] = []
        self._routed = False

    def answer_with(self, reply: StubReply) -> None:
        """Routes the endpoint to this stub on the first call; a later call only changes the reply."""
        self._reply = reply
        if not self._routed:
            self._page.route(self._endpoint, self._answer)
            self._routed = True

    def capture_one(self, action: Callable[[], object]) -> AnsweredRequest:
        answered_before = len(self._answered)
        with self._page.expect_response(self._endpoint, timeout=CAPTURE_TIMEOUT_MS) as response_info:
            action()
        if response_info.value.from_service_worker:
            raise InterceptionNotProvenError(self._endpoint, "a service worker answered it")
        if len(self._answered) != answered_before + 1:
            raise InterceptionNotProvenError(
                self._endpoint, f"answered {len(self._answered) - answered_before}"
            )
        return self._answered[-1]

    def expect_none_during(self, action: Callable[[], object]) -> None:
        """Runs `action` and fails if the endpoint is called within the quiet window after it."""
        try:
            with self._page.expect_request(self._endpoint, timeout=QUIET_WINDOW_MS):
                action()
        except PlaywrightTimeoutError:
            return
        raise UnexpectedRequestError(self._endpoint)

    def answered_once_things_settle(self) -> int:
        """How many requests the stub answered, counted once no new one came for a quiet window."""
        while self._another_request_comes():
            continue
        return len(self._answered)

    def _another_request_comes(self) -> bool:
        try:
            with self._page.expect_request(self._endpoint, timeout=QUIET_WINDOW_MS):
                pass
        except PlaywrightTimeoutError:
            return False
        return True

    def _answer(self, route: Route) -> None:
        request = route.request
        self._answered.append(AnsweredRequest(request.method, request.url, request.post_data))
        route.fulfill(
            status=self._reply.status, content_type="application/json", body=json.dumps(self._reply.payload)
        )
