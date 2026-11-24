"""J35 data-sync-offline: what the web app shows when the connection drops (DS-01..DS-04, DS-26).

DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

import pytest
from playwright.sync_api import Page

from pages.data_sync.connection import Connectivity, HeaderConnectionIcon, NoInternetOverlay, PageIdentity
from pages.data_sync.offline_bill import SAVE_ENDPOINT, OfflineBill
from pages.data_sync.request_log import RequestLog
from pages.login_page import LoginPage

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]


def test_going_offline_covers_the_screen_with_the_no_internet_overlay(
    layout_page: Page, connectivity: Connectivity
) -> None:
    connectivity.go_offline()

    NoInternetOverlay(layout_page).expect_shown()


def test_going_online_again_removes_the_overlay_without_a_reload(
    layout_page: Page, connectivity: Connectivity
) -> None:
    overlay = NoInternetOverlay(layout_page)
    document = PageIdentity(layout_page)
    document.mark()
    connectivity.go_offline()
    overlay.expect_shown()

    connectivity.go_online()

    overlay.expect_gone()
    assert document.is_same_document(), "DS-02: the page reloaded to recover from the lost connection"


def test_offline_header_shows_the_no_wifi_icon(layout_page: Page, connectivity: Connectivity) -> None:
    connectivity.go_offline()

    HeaderConnectionIcon(layout_page).expect_offline_icon()


def test_offline_click_on_save_reaches_the_overlay_and_sends_no_bill(sale_bill_page: Page) -> None:
    bill = OfflineBill(sale_bill_page)
    bill.fill()
    save_requests = RequestLog(sale_bill_page, SAVE_ENDPOINT)
    connectivity = Connectivity(sale_bill_page)
    connectivity.go_offline()
    NoInternetOverlay(sale_bill_page).expect_shown()

    bill.click_save()
    connectivity.go_online()

    NoInternetOverlay(sale_bill_page).expect_gone()
    bill.expect_still_open()
    assert save_requests.urls == (), (
        f"DS-04: the click behind the overlay started a save: {save_requests.urls}"
    )


def test_overlay_covers_the_login_screen_too(page: Page) -> None:
    LoginPage(page).open()

    Connectivity(page).go_offline()

    NoInternetOverlay(page).expect_shown()
