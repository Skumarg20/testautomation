"""J35 data-sync-offline: the web Data Sync request screen, read only (DS-14..DS-17, DS-23).

Enable Data Sync and Cancel are never pressed online here: on the shared company both change
`tbldataSyncRequest` for good (DS-18/DS-19 need a throwaway company). DS-17 presses Enable only offline,
where the browser cannot send anything even if the app's guard were missing.
DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

from datetime import date

import pytest
from playwright.sync_api import Page, expect

from pages.data_sync.connection import Connectivity, NoInternetOverlay
from pages.data_sync.data_sync_form import DataSyncForm
from pages.data_sync.data_sync_screen import REQUEST_ENDPOINT, DataSyncScreen
from pages.data_sync.menu import DATA_SYNC_DETAILS, MULTI_EDITING, OtherToolsMenu
from pages.data_sync.request_log import RequestLog

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]

NO_INTERNET_WARNING = "Internet Required for this option!"


@pytest.fixture
def data_sync_screen(layout_page: Page) -> DataSyncScreen:
    screen = DataSyncScreen(layout_page)
    screen.open()
    return screen


def test_screen_shows_company_email_and_todays_report_date(data_sync_screen: DataSyncScreen) -> None:
    data_sync_screen.expect_company_email()

    data_sync_screen.expect_report_date(date.today())


def test_screen_offers_no_electron_grid_or_upload(data_sync_screen: DataSyncScreen) -> None:
    data_sync_screen.expect_no_electron_controls()


def test_request_strip_shows_exactly_one_request_state(data_sync_screen: DataSyncScreen) -> None:
    states = data_sync_screen.shown_states()

    assert len(states) == 1, f"DS-16: the request strip shows {states or 'no state'}, expected exactly one"


def test_other_tools_menu_does_not_list_data_sync_details(layout_page: Page) -> None:
    menu = OtherToolsMenu(layout_page)

    menu.open_other_tools()

    expect(menu.entry(MULTI_EDITING)).to_be_visible()
    expect(menu.entry(DATA_SYNC_DETAILS)).to_have_count(0)


def test_offline_enable_data_sync_asks_for_internet_and_sends_nothing(
    data_sync_screen: DataSyncScreen, layout_page: Page
) -> None:
    if not data_sync_screen.enable_button.is_visible():
        pytest.skip("DS-17: the company already has a request, so Enable Data Sync is not offered")
    sync_requests = RequestLog(layout_page, REQUEST_ENDPOINT)
    Connectivity(layout_page).go_offline()
    NoInternetOverlay(layout_page).expect_shown()

    data_sync_screen.press_enable_with_keyboard()

    expect(layout_page.get_by_text(NO_INTERNET_WARNING)).to_be_visible()
    assert sync_requests.urls == (), f"DS-17: a sync request was attempted offline: {sync_requests.urls}"


def test_public_data_sync_route_keeps_its_electron_form_hidden(layout_page: Page) -> None:
    form = DataSyncForm(layout_page)

    form.open()

    form.expect_built_but_hidden()
