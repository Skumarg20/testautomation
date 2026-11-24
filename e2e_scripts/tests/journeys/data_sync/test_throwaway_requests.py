"""J35 data-sync-offline: sending and cancelling a real data sync request (DS-18, DS-19).

Both write `tbldataSyncRequest` for the company for good: a cancelled request can never be sent again
(`OfflineOnlineDataSync.cs:2090-2113`). They run only on the throwaway company (`test_data/data_sync.py`),
skip when it is missing or not in the state they need, and are `permanent`, so a run includes them only with
`--allow-permanent`. Run DS-18 first: it leaves the pending request DS-19 cancels.
DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.components.confirm_dialog import ConfirmDialog
from pages.data_sync.data_sync_screen import DataSyncScreen, SyncRequestState

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]

ACCEPTED = "Request has been accepted!"
CANCEL_QUESTION = "You Won't be able to send request again. Are you sure want to cancel ?"


def _screen_in_state(page: Page, state: SyncRequestState, scenario: str) -> DataSyncScreen:
    screen = DataSyncScreen(page)
    screen.open()
    if state not in screen.shown_states():
        pytest.skip(f"{scenario}: the throwaway company's request is not in the state {state.name}")
    return screen


@pytest.mark.permanent("a pending data sync request on the throwaway company")
def test_enable_data_sync_sends_a_pending_request(throwaway_page: Page) -> None:
    screen = _screen_in_state(throwaway_page, SyncRequestState.NO_REQUEST, "DS-18")

    screen.press_enable()

    expect(throwaway_page.get_by_text(ACCEPTED).first).to_be_visible()
    screen.expect_state(SyncRequestState.PENDING)
    expect(screen.cancel_button).to_be_visible()


@pytest.mark.permanent("a cancelled data sync request on the throwaway company (cannot be sent again)")
def test_cancelling_a_pending_request_marks_it_cancelled(throwaway_page: Page) -> None:
    screen = _screen_in_state(throwaway_page, SyncRequestState.PENDING, "DS-19")
    screen.press_cancel()
    dialog = ConfirmDialog(throwaway_page)
    dialog.expect_asking(CANCEL_QUESTION)

    dialog.answer_yes()

    screen.expect_state(SyncRequestState.CANCELLED)
    expect(screen.enable_button).to_have_count(0)
