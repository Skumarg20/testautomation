"""J35 data-sync-offline: starting the app or signing in without a connection (DS-25, DS-26 submit part).

DS-25 needs the app's service worker, which every other context blocks; `service_worker_page` is a form
login in a context of its own that allows it (`app.module.ts:191-194`, enabled in the preprod build). With
the worker, a reload offline should still draw the app shell, and the root component then shows its offline
overlay. DS-26: the overlay covers the login form, but Enter still submits it; the login call fails with
status 0, which the pack expects to end on `/error` (UNVERIFIED, N4). The credentials are dummies: offline
nothing leaves. DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app
yet.
"""

import pytest
from playwright.sync_api import Page

from pages.data_sync.connection import Connectivity, NoInternetOverlay
from pages.data_sync.maintenance_page import MaintenancePage
from pages.data_sync.offline_login import OfflineLogin

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]

OFFLINE_USER = "offline.check"
OFFLINE_PASSWORD = "not-sent"


def test_reload_while_offline_draws_the_app_shell_with_the_overlay(service_worker_page: Page) -> None:
    Connectivity(service_worker_page).go_offline()

    service_worker_page.reload()

    NoInternetOverlay(service_worker_page).expect_shown()


def test_login_submitted_offline_ends_on_the_maintenance_page(page: Page) -> None:
    login = OfflineLogin(page)
    login.open()
    Connectivity(page).go_offline()
    NoInternetOverlay(page).expect_shown()

    login.submit_with_keyboard(OFFLINE_USER, OFFLINE_PASSWORD)

    MaintenancePage(page).expect_shown()
