"""Manual case 162: a user without the Sale right cannot open the sale bill.

Uses the suite's `operator` and `accountant` logins (skipped through `page_as` when a run has no credentials
for them). Whether such a login lacks the Sale right is not recorded, so the test looks at the side menu first
and skips when the Sale entry is there. The sale bill list is `/sale/salebook` (Modules/sales.module.ts:23);
a role without the right is sent away or shown the app's denial page (`AccessDenied`).
"""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.waiting import appears_within
from pages.components.access_denied import AccessDenied
from pages.dashboard_page import DashboardPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("role-based-access")]

SALE_BILL_LIST = "/sale/salebook"
SALE_MENU = re.compile(r"^Sale( Sale)?$")
MENU_LOOKUP_MS = 10_000


@pytest.mark.parametrize("account", ["operator", "accountant"])
def test_role_without_the_sale_right_cannot_open_the_sale_bill(
    page_as: Callable[[Account], Page], account: Account
) -> None:
    page = page_as(account)
    DashboardPage(page).open()
    if appears_within(page.get_by_role("link", name=SALE_MENU), MENU_LOOKUP_MS):
        pytest.skip(f"the {account} login has the Sale right")

    AccessDenied(page).expect_denied(SALE_BILL_LIST)
