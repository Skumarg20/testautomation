"""J35 data-sync-offline: the header speed widget and the slow-internet banner (DS-03, DS-13, DS-48).

Each test holds Control Room "Show Internet Speed" at the value it needs and puts the tenant's value back,
so the module runs in xdist group "chemist-tenant" (CLAUDE.md rule 0). DS-13 makes the browser report a
fixed `navigator.connection.downlink` instead of throttling the network (see `ReportedDownlink`).
DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

import pytest
from playwright.sync_api import Page

from pages.data_sync.connection import Connectivity
from pages.data_sync.internet_speed import InternetSpeedWidget, SlowInternetBanner

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("data-sync-offline"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def test_speed_widget_shows_a_reading_when_the_setting_is_on(speed_shown_page: Page) -> None:
    InternetSpeedWidget(speed_shown_page).expect_shown()


def test_speed_widget_and_banner_are_absent_when_the_setting_is_off(speed_hidden_page: Page) -> None:
    widget = InternetSpeedWidget(speed_hidden_page)

    widget.expect_absent()

    SlowInternetBanner(speed_hidden_page).expect_absent()


def test_offline_header_hides_the_speed_widget(speed_shown_page: Page) -> None:
    widget = InternetSpeedWidget(speed_shown_page)
    widget.expect_shown()

    Connectivity(speed_shown_page).go_offline()

    widget.expect_absent()


def test_link_below_two_megabits_shows_the_slow_internet_banner(slow_link_page: Page) -> None:
    SlowInternetBanner(slow_link_page).expect_shown()


def test_fast_link_shows_no_slow_internet_banner(fast_link_page: Page) -> None:
    InternetSpeedWidget(fast_link_page).expect_fast_bars()

    SlowInternetBanner(fast_link_page).expect_absent()
