"""A logged-out page whose OTP/mail requests are blocked; the test fails if any was attempted."""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Page

from pages.auth.dispatch_guard import DispatchGuard


@pytest.fixture
def guarded_page(page: Page) -> Iterator[Page]:
    guard = DispatchGuard(page)
    guard.install()
    yield page
    guard.expect_nothing_dispatched()
