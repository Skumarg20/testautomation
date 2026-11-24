"""Data Sync request screen at `/other/datasyncreport`, reachable on the web by URL only (J35 DS-14..DS-17).

On the web (isElectron 0) it shows the heading, the company e-mail, today's report date and a request strip:
a status text and "Enable Data Sync" (no request) or "Cancel" (pending). The grid, Add, Refresh and Upload
are Electron-only (`data-sync.Reportcomponent.html:8-149`; `data-syncreport.component.ts:49-58`, `:200-226`).
The strip asks `SetGetdatasyncsetting` first and `SyncRequeststatus` only when that answers 0.
Never press Enable or Cancel online on a shared company: both change `tbldataSyncRequest` for good.
DRAFT: locators from the Angular source, not seen live.
"""

import re
from datetime import date
from enum import Enum

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage

PATH = "/other/datasyncreport"
HEADING = "Data Sync"
EMAIL_CAPTION = "Currently logged in with the following Email:"
REPORT_DATE_FORMAT = "%d-%m-%Y"
SETTING_ENDPOINT = re.compile(r"OfflineOnline/SetGetdatasyncsetting", re.IGNORECASE)
STATUS_ENDPOINT = re.compile(r"OfflineOnline/SyncRequeststatus", re.IGNORECASE)
REQUEST_ENDPOINT = re.compile(r"OfflineOnline/SyncRequestsave", re.IGNORECASE)
SCREEN_TIMEOUT_MS = 60_000
# The status call follows the setting call at once when there is one; past this there is none.
STATUS_CALL_TIMEOUT_MS = 15_000
COMPANY_EMAIL_LINE = re.compile(rf"{re.escape(EMAIL_CAPTION)}\s*\S+@\S+\.\S+")
ELECTRON_ONLY_BUTTONS = re.compile(r"^\s*(Add|Refresh|Upload)\b", re.IGNORECASE)
ENABLE = re.compile(r"^\s*Enable\s+Data Sync\s*$")
CANCEL = re.compile(r"^\s*Cancel\s*$")
# Why CSS: the screen has no test id or landmark; its component host element is the only handle that keeps
# the checks inside this screen and away from the layout's own buttons.
SCREEN_HOST = "app-data-syncreport"
# Why CSS: ag-Grid renders no role until it has rows; the element tag is the only sign of the grid.
GRID_HOST = "ag-grid-angular"


class SyncRequestState(Enum):
    """The strip's four states, by the status text it prints (`data-syncreport.component.ts:210-216`)."""

    PENDING = "Your request is pending for approval"
    APPROVED = "Your request has been approved!"
    CANCELLED = "Your data sync request is cancelled by Admin..."
    NO_REQUEST = ""


class DataSyncScreen(BasePage):
    def open(self) -> None:
        """Opens the screen and waits until the request strip has had its answer."""
        with self.page.expect_response(SETTING_ENDPOINT, timeout=SCREEN_TIMEOUT_MS):
            self.goto(PATH, SCREEN_TIMEOUT_MS)
        self._wait_for_status_call()
        expect(self.heading).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", name=HEADING, exact=True)

    @property
    def enable_button(self) -> Locator:
        return self._screen.get_by_role("button", name=ENABLE)

    @property
    def cancel_button(self) -> Locator:
        return self._screen.get_by_role("button", name=CANCEL)

    def expect_company_email(self) -> None:
        expect(self._screen).to_contain_text(COMPANY_EMAIL_LINE)

    def expect_report_date(self, day: date) -> None:
        report_date = re.escape(day.strftime(REPORT_DATE_FORMAT))
        expect(self._screen).to_contain_text(re.compile(rf"Report Date:\s*{report_date}"))

    def expect_no_electron_controls(self) -> None:
        expect(self._screen.locator(GRID_HOST)).to_have_count(0)
        expect(self._screen.get_by_role("button", name=ELECTRON_ONLY_BUTTONS)).to_have_count(0)
        expect(self._screen.get_by_text("Particulars Name")).to_have_count(0)

    def shown_states(self) -> list[SyncRequestState]:
        """Every request state the strip shows now; a consistent strip shows exactly one."""
        return [state for state in SyncRequestState if self._shows(state)]

    def expect_state(self, state: SyncRequestState) -> None:
        if state is SyncRequestState.NO_REQUEST:
            expect(self.enable_button).to_be_visible(timeout=STATUS_CALL_TIMEOUT_MS)
            return
        expect(self._screen.get_by_text(state.value)).to_be_visible(timeout=STATUS_CALL_TIMEOUT_MS)

    def press_enable(self) -> None:
        """Online this writes a request for the company for good: throwaway company only (DS-18)."""
        self.enable_button.click()

    def press_cancel(self) -> None:
        """Asks for confirmation first (`data-syncreport.component.ts:187-193`)."""
        self.cancel_button.click()

    def press_enable_with_keyboard(self) -> None:
        """Enter on the focused button: the keyboard still reaches it while the offline overlay hides it."""
        self.enable_button.focus()
        self.page.keyboard.press("Enter")

    def _shows(self, state: SyncRequestState) -> bool:
        if state is SyncRequestState.NO_REQUEST:
            return self._shows_no_request()
        return self._screen.get_by_text(state.value).is_visible()

    def _shows_no_request(self) -> bool:
        any_status = "|".join(re.escape(s.value) for s in SyncRequestState if s.value)
        no_status_text = not self._screen.get_by_text(re.compile(any_status)).is_visible()
        return no_status_text and self.enable_button.is_visible()

    def _wait_for_status_call(self) -> None:
        """Waits for the status answer when one is coming; its absence is the "no request" case."""
        try:
            with self.page.expect_response(STATUS_ENDPOINT, timeout=STATUS_CALL_TIMEOUT_MS):
                pass
        except PlaywrightTimeoutError:
            return

    @property
    def _screen(self) -> Locator:
        return self.page.locator(SCREEN_HOST)
