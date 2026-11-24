"""Asserts that a restricted page is not available to the signed-in role."""

import re

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage

DENIAL_WAIT_MS = 15_000
DENIAL_WORDING = re.compile(
    r"access denied|not authori[sz]ed|no permission|permission denied|forbidden", re.I
)
IS_DENIED_SCRIPT = """
([restrictedPath, wording]) =>
    !window.location.pathname.startsWith(restrictedPath)
        || new RegExp(wording, 'i').test(document.body.innerText)
"""


class AccessDeniedError(AssertionError):
    def __init__(self, path: str) -> None:
        super().__init__(f"{path} was reachable: no redirect and no denial message appeared")


class AccessDenied(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def expect_denied(self, path: str) -> None:
        """Passes when opening `path` redirects elsewhere or shows denial wording."""
        self.goto(path)
        try:
            self.page.wait_for_function(
                IS_DENIED_SCRIPT, arg=[path, DENIAL_WORDING.pattern], timeout=DENIAL_WAIT_MS
            )
        except PlaywrightTimeoutError:
            raise AccessDeniedError(path) from None
