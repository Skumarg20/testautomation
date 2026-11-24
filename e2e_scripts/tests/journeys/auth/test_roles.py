from collections.abc import Callable

import pytest
from playwright.sync_api import Locator, Page

from config.settings import Account
from pages.dashboard_page import DashboardPage

pytestmark = [pytest.mark.p0, pytest.mark.journey("role-based-access")]

SUPER_ADMIN: Account = "garments"
TOP_MENU = (
    "Dashboard",
    "Master",
    "Sale",
    "Purchase",
    "Accounting Trans.",
    "Stock Management",
    "Banking",
    "Staff Register",
    "Report",
    "Other Products",
    "CRM",
    "Utilities & Tools",
    "Online Store",
)
ROLE_RIGHT_KEYS = ("RoleRight", "Commonrigths")
LOCAL_STORAGE_KEYS = "() => Object.keys(localStorage)"
# Each admin page with a locator only that screen renders (same signals as UserMasterPage and
# CommunicationSettings). /companymaster has no page object yet, so it only proves the main region rendered.
ADMIN_PAGES: dict[str, Callable[[Page], Locator]] = {
    "/mstr/usermaster": lambda page: page.get_by_role("button", name="Invite User"),
    "/mstr/margsetup-controlroom": lambda page: page.get_by_role("main").get_by_role(
        "heading", name="Control Room", level=1
    ),
    "/companymaster": lambda page: page.get_by_role("main"),
}


def test_super_admin_sees_every_top_level_menu(page_as: Callable[[Account], Page]) -> None:
    dashboard = DashboardPage(page_as(SUPER_ADMIN))
    dashboard.open()

    dashboard.expect_menu_items(TOP_MENU)


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_super_admin_can_open_admin_page(page_as: Callable[[Account], Page], path: str) -> None:
    page = page_as(SUPER_ADMIN)
    DashboardPage(page).open()
    DashboardPage(page).expect_menu_items(("Master",))

    page.goto(path)

    DashboardPage(page).expect_page_open(path, ADMIN_PAGES[path](page))


def test_session_holds_the_role_rights(page_as: Callable[[Account], Page]) -> None:
    page = page_as(SUPER_ADMIN)
    DashboardPage(page).open()
    DashboardPage(page).expect_loaded()

    local_keys = " ".join(page.evaluate(LOCAL_STORAGE_KEYS))

    assert all(name in local_keys for name in ROLE_RIGHT_KEYS), local_keys


@pytest.mark.skip(
    reason="RB-03: roles are made per tenant with per-menu powers (careportal:296923), so the role matrix "
    "(Q4) is whatever the supervisor configures. A user without View right should be stopped with an alert "
    "(Jira MBC-5372; careportal:308208 'Not Authorised'), but the route guard does not check role rights "
    "(route-mapping.md 'Guards and rights') and the API does not enforce them (role-management-flow.md). "
    "No limited account exists. Question (Q3): what must a limited user see on /mstr/usermaster, the "
    "Control Room and /companymaster, and is the missing guard/API check accepted or a defect?"
)
@pytest.mark.parametrize("role", ["operator", "accountant"])
def test_limited_role_is_denied_admin_pages(role: Account) -> None:
    """Placeholder until RB-03 is answered; it must not spend a login while skipped."""
