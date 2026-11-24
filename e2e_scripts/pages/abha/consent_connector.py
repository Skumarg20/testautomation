"""The external ABHA consent site the selection popup's "Patient History" opens in a new tab
(`abha-selection-component.ts:71-75`, pack finding 1).

The tab's address carries a hard-coded institute and token. The stub answers the tab's request with an
empty page, so nothing reaches the site, and the test only learns yes/no facts about the address: the URL
itself is never returned, logged or put in an assertion message.

The stub is a context route registered after the `SendGuard`'s, so it is matched first (Playwright runs
routes in reverse order of registration) and covers the new tab.
"""

import re
from collections.abc import Callable
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, Route

CONSENT_CONNECTOR = re.compile(r"//abhaconnector\.", re.IGNORECASE)
CONSENT_PATH = "/consents"
HIP_REQUEST = "hip"
EMPTY_PAGE = "<!doctype html><title>QA stub</title><p>QA stub: consent site not contacted</p>"
TAB_TIMEOUT_MS = 15_000


class ConsentTabNotStubbedError(AssertionError):
    def __init__(self) -> None:
        super().__init__("The consent tab's request was not answered by the stub")


class ConsentPageNotOpenedError(AssertionError):
    def __init__(self) -> None:
        super().__init__(
            "The new tab is not the connector's HIP consent page (address withheld: it has a token)"
        )


class ConsentConnectorStub:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._answered = 0

    def install(self) -> None:
        self._page.context.route(CONSENT_CONNECTOR, self._answer)

    def expect_consent_tab_from(self, action: Callable[[], object]) -> None:
        answered_before = self._answered
        with self._page.expect_popup(timeout=TAB_TIMEOUT_MS) as tab_info:
            action()
        tab = tab_info.value
        tab.wait_for_load_state("load", timeout=TAB_TIMEOUT_MS)
        if self._answered <= answered_before:
            raise ConsentTabNotStubbedError()
        if not _is_hip_consent_page(tab.url):
            raise ConsentPageNotOpenedError()
        tab.close()

    def _answer(self, route: Route) -> None:
        self._answered += 1
        route.fulfill(status=200, content_type="text/html", body=EMPTY_PAGE)


def _is_hip_consent_page(url: str) -> bool:
    address = urlsplit(url)
    return (
        "abhaconnector" in address.netloc
        and address.path == CONSENT_PATH
        and parse_qs(address.query).get("type") == [HIP_REQUEST]
    )
