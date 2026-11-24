"""What the app shows after an action: the loading spinner, toasts and the Yes/No confirmation."""

import re
from enum import Enum

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.accounting.confirmation import Confirmation
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

# appears_within is re-exported for the purchase pages that still import it from here.
__all__ = ["AppFeedback", "ToastKind", "appears_within"]

LOADER_APPEAR_TIMEOUT_MS = 2_000
LOADER_GONE_TIMEOUT_MS = 90_000
TOAST_TIMEOUT_MS = 15_000
TOAST_GONE_TIMEOUT_MS = 10_000
CONFIRM_TIMEOUT_MS = 2_000


class ToastKind(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class AppFeedback(BasePage):
    def wait_for_loader(self) -> None:
        """The spinner may be too quick to catch, so a spinner that never shows is not an error."""
        if appears_within(self._loader, LOADER_APPEAR_TIMEOUT_MS):
            expect(self._loader.first).to_be_hidden(timeout=LOADER_GONE_TIMEOUT_MS)

    def expect_toast(self, kind: ToastKind, timeout_ms: int = TOAST_TIMEOUT_MS) -> None:
        toast = self._toast(kind)
        expect(toast.first).to_be_visible(timeout=timeout_ms)
        self._dismiss(toast)

    def expect_toast_saying(self, kind: ToastKind, message: str, timeout_ms: int = TOAST_TIMEOUT_MS) -> None:
        """Waits for a toast of this kind whose text contains `message` (any case), then dismisses it."""
        toast = self._toast_saying(kind, message)
        expect(toast.first).to_be_visible(timeout=timeout_ms)
        self._dismiss(toast)

    def toast_appears_saying(self, kind: ToastKind, message: str, timeout_ms: int) -> bool:
        return appears_within(self._toast_saying(kind, message), timeout_ms)

    def any_toast(self) -> Locator:
        return self.page.locator("notifier-notification")

    def toast_appears(self, kind: ToastKind, timeout_ms: int) -> bool:
        return appears_within(self._toast(kind), timeout_ms)

    def confirm_if_asked(self) -> None:
        """Presses Yes on the app's confirmation box when one opens."""
        Confirmation(self.page).answer_yes_if_asked(CONFIRM_TIMEOUT_MS)

    def close_stacked_modals(self) -> None:
        """Closes all but the newest dialog; older ones stay in the page and swallow clicks."""
        # Angular keeps older dialogs in the DOM with aria-hidden set, so they are counted too.
        dialogs = self.page.locator("ngb-modal-window[aria-modal='true']")
        while (count := dialogs.count()) > 1:
            newest = dialogs.last
            close = newest.locator("button[aria-label='Close'], .close").first
            if close.is_visible():
                close.click()
            else:
                self.page.keyboard.press("Escape")
            expect(dialogs).to_have_count(count - 1, timeout=CONFIRM_TIMEOUT_MS)

    @property
    def _loader(self) -> Locator:
        # The spinner is an SVG circle that has only an id (with a space in it) to find it by.
        return self.page.locator('[id="Ellipse 363"]')

    def _toast(self, kind: ToastKind) -> Locator:
        # Toasts are notifier-notification elements, told apart by a modifier class only.
        return self.page.locator(f"notifier-notification.notifier__notification--{kind.value}")

    def _toast_saying(self, kind: ToastKind, message: str) -> Locator:
        return self._toast(kind).filter(has_text=re.compile(re.escape(message), re.IGNORECASE))

    def _dismiss(self, toast: Locator) -> None:
        close = self.page.get_by_title("dismiss")
        if appears_within(close, CONFIRM_TIMEOUT_MS):
            close.first.click()
        try:
            toast.first.wait_for(state="hidden", timeout=TOAST_GONE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            return  # the original treats a toast that lingers as a soft failure; later steps tolerate it
