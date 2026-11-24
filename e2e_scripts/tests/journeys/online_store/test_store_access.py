"""J37 a limited user cannot open the online store by URL (OS-37).

Uses the suite's `operator` role login, which must lack the Online Store and Sale rights; the test skips
(through `page_as`) when the run has no operator credentials. Expected value UNVERIFIED (pack checklist).
"""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.components.access_denied import AccessDenied
from pages.dashboard_page import DashboardPage
from pages.online_store.entry import CREATE_STORE_PATH, ORDER_DASHBOARD_PATH

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

LIMITED_ACCOUNT: Account = "operator"


@pytest.mark.parametrize("path", [CREATE_STORE_PATH, ORDER_DASHBOARD_PATH])
def test_limited_user_is_denied_the_online_store(page_as: Callable[[Account], Page], path: str) -> None:
    """OS-37: the store pages are denied or redirected away.

    `/other/onlinestore` itself always redirects (it is only a router), so its two targets are opened.
    """
    page = page_as(LIMITED_ACCOUNT)
    DashboardPage(page).open()
    AccessDenied(page).expect_denied(path)
