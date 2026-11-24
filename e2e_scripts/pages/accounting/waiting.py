"""Short, tolerant visibility checks. The app shows many popups only sometimes, so absence is not an error."""

from playwright.sync_api import Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def appears_within(target: Locator, timeout_ms: int) -> bool:
    try:
        target.first.wait_for(state="visible", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return False
    return True


def disappears_within(target: Locator, timeout_ms: int) -> bool:
    try:
        target.first.wait_for(state="hidden", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return False
    return True
