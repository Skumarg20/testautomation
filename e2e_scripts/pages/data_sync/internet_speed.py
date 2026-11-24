"""The header's internet-speed widget and the red "slow internet" banner (J35 DS-03, DS-13, DS-48).

Both run only when Control Room "Show Internet Speed" is on (profiler InternetSpeed "T") and the browser
reports `navigator.connection.downlink`; every 5 s the layout copies `downlink` into "<n> Mb/s" and sets
red (0 < n < 2), yellow (2 < n < 6) or light green (n > 6) (`homelayout.component.ts:771-786`, `:1096`).
The banner shows on red (`homeLayout.component.html:1-10`). DRAFT: locators from the Angular source.
"""

import re

from playwright.sync_api import BrowserContext, Locator, expect

from pages.base_page import BasePage

INTERNET_SPEED_SWITCH = "Show Internet Speed"
SLOW_BANNER_TEXT = "Slow internet connection. Please check your internet setting"
# The layout re-reads the speed every 5 s; one full cycle plus the first paint of the layout.
SPEED_CYCLE_TIMEOUT_MS = 20_000
SPEED_READING = re.compile(r"Mb/s\s*$")
# The app version sits next to the widget in the same header block; once it shows, the header is drawn.
HEADER_VERSION = re.compile(r"^\s*V\. \d")
# Why CSS: the speed bars are an unnamed svg whose colour is only in the paths' fill attribute.
FAST_SPEED_BARS = 'path[fill="lightgreen"]'
# Chromium's real `downlink` depends on the machine running the test, so the test reports a fixed one.
# Only the property the layout reads is replaced; the app's speed logic itself is what is tested.
REPORTED_DOWNLINK_SCRIPT = """
(downlink) => {
    const connection = { downlink, effectiveType: '4g', addEventListener() {}, removeEventListener() {} };
    Object.defineProperty(Navigator.prototype, 'connection', { get: () => connection, configurable: true });
}
"""


class ReportedDownlink:
    """Makes every page of a context report a fixed `navigator.connection.downlink` in Mb/s."""

    def __init__(self, context: BrowserContext) -> None:
        self._context = context

    def report(self, megabits_per_second: float) -> None:
        self._context.add_init_script(script=f"({REPORTED_DOWNLINK_SCRIPT})({megabits_per_second});")


class InternetSpeedWidget(BasePage):
    """The "<n> Mb/s" reading with its wifi bars, next to the version number in the header."""

    @property
    def reading(self) -> Locator:
        return self.page.get_by_text(SPEED_READING)

    def expect_shown(self) -> None:
        expect(self.reading.first).to_be_visible(timeout=SPEED_CYCLE_TIMEOUT_MS)

    def expect_absent(self) -> None:
        """Checked once the header is drawn, so an absence before the layout renders proves nothing."""
        expect(self.page.get_by_text(HEADER_VERSION).first).to_be_visible(timeout=SPEED_CYCLE_TIMEOUT_MS)
        expect(self.reading).to_have_count(0, timeout=SPEED_CYCLE_TIMEOUT_MS)

    def expect_fast_bars(self) -> None:
        bars = self.page.locator(FAST_SPEED_BARS)
        expect(bars.first).to_be_attached(timeout=SPEED_CYCLE_TIMEOUT_MS)


class SlowInternetBanner(BasePage):
    @property
    def banner(self) -> Locator:
        return self.page.get_by_text(SLOW_BANNER_TEXT)

    def expect_shown(self) -> None:
        expect(self.banner).to_be_visible(timeout=SPEED_CYCLE_TIMEOUT_MS)

    def expect_absent(self) -> None:
        expect(self.banner).to_have_count(0)
