"""Fixtures for user and role management (J15): the User List page and a test-owned role deleted after."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.admin.user_master_page import ROLE_SAVED, UserMasterPage
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from test_data.user_roles import RoleSpec, new_role

# The super admin login; every configured account is this one user (specs/user-role-management.md).
SUPER_ADMIN: Account = "garments"
CLEANUP_ATTEMPTS = 3


class RoleCleanupError(AssertionError):
    def __init__(self, name: str, left: int) -> None:
        super().__init__(f"Role {name!r} is still listed {left} time(s) after {CLEANUP_ATTEMPTS} deletes")


@pytest.fixture
def user_master(company_page: Callable[[Account, str], Page]) -> UserMasterPage:
    # Whether roles are per company or per login is open (UR-15); the plan was observed on this company.
    page = company_page(SUPER_ADMIN, GARMENTS_COMPANY)
    DashboardPage(page).expect_menu_items(("Master",))
    return UserMasterPage(page)


@pytest.fixture
def role(run_id: str, user_master: UserMasterPage) -> Iterator[RoleSpec]:
    """A role owned by this test; every role with its run-id name is deleted afterwards (even duplicates)."""
    owned = new_role(run_id)
    yield owned
    _delete_every_copy(user_master, owned.name)


@pytest.fixture
def saved_role(role: RoleSpec, user_master: UserMasterPage) -> RoleSpec:
    user_master.open_roles()
    configuration = user_master.start_new_role()
    configuration.fill_name(role.name)
    configuration.fill_description(role.description)
    configuration.grant_full(role.right)
    configuration.save()
    user_master.expect_message(ROLE_SAVED)
    configuration.expect_closed()
    return role


def _delete_every_copy(user_master: UserMasterPage, name: str) -> None:
    for _ in range(CLEANUP_ATTEMPTS):
        user_master.open_roles()
        if user_master.role_count(name) == 0:
            return
        user_master.delete_role(name)
    user_master.open_roles()
    left = user_master.role_count(name)
    if left:
        raise RoleCleanupError(name, left)
