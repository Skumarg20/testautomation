"""Opening a screen with a keyboard shortcut. The app ignores shortcuts until its handlers are ready."""

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ATTEMPTS = 4
ATTEMPT_TIMEOUT_MS = 10_000


class ShortcutIgnoredError(RuntimeError):
    def __init__(self, shortcut: str) -> None:
        super().__init__(f"The app did not react to {shortcut} after {ATTEMPTS} attempts")


def press_until_visible(page: Page, shortcut: str, ready: Locator) -> None:
    for _ in range(ATTEMPTS):
        page.keyboard.press(shortcut)
        try:
            ready.wait_for(state="visible", timeout=ATTEMPT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            continue
        return
    raise ShortcutIgnoredError(shortcut)
