"""J15 user and role management: roles are created, edited and deleted; predefined roles are protected.

Plan: specs/user-role-management.md (UR-01 to UR-09). Users are not created: the plan's seat limit is reached
and an invite sends a real message (NEEDS DECISION UR-D1).
"""

import pytest

from pages.admin.user_master_page import PREDEFINED_REFUSAL, ROLE_SAVED, UserMasterPage
from test_data.user_roles import LEDGER_MASTER_RIGHT, MASTER_MENU, PREDEFINED_ROLE, Right, RoleSpec

pytestmark = [pytest.mark.p1, pytest.mark.journey("user-role-management")]

LEDGER_MASTER = Right(MASTER_MENU, LEDGER_MASTER_RIGHT)
EDITED_DESCRIPTION_SUFFIX = " edited"


def test_new_role_is_listed_with_its_description(saved_role: RoleSpec, user_master: UserMasterPage) -> None:
    user_master.open_roles()

    user_master.expect_role_listed(saved_role.name, saved_role.description)


def test_right_granted_at_create_is_kept(saved_role: RoleSpec, user_master: UserMasterPage) -> None:
    user_master.open_roles()

    configuration = user_master.edit_role(saved_role.name)

    configuration.expect_shows(saved_role.name, saved_role.description)
    configuration.expect_full_granted(saved_role.right)


def test_full_right_ticks_every_right_of_that_screen(user_master: UserMasterPage) -> None:
    user_master.open_roles()
    configuration = user_master.start_new_role()

    configuration.grant_full(LEDGER_MASTER)

    configuration.expect_every_right_checked(LEDGER_MASTER)
    configuration.close()


def test_edited_rights_and_description_are_kept(saved_role: RoleSpec, user_master: UserMasterPage) -> None:
    edited_description = saved_role.description + EDITED_DESCRIPTION_SUFFIX
    user_master.open_roles()
    configuration = user_master.edit_role(saved_role.name)
    configuration.fill_description(edited_description)
    configuration.grant_full(LEDGER_MASTER)
    configuration.update()
    user_master.expect_message(ROLE_SAVED)

    user_master.open_roles()
    reopened = user_master.edit_role(saved_role.name)

    reopened.expect_shows(saved_role.name, edited_description)
    reopened.expect_every_right_checked(LEDGER_MASTER)


def test_deleted_role_leaves_the_list(saved_role: RoleSpec, user_master: UserMasterPage) -> None:
    user_master.open_roles()

    user_master.delete_role(saved_role.name)

    user_master.expect_role_not_listed(saved_role.name)


def test_role_without_a_name_is_not_saved(user_master: UserMasterPage) -> None:
    user_master.open_roles()
    configuration = user_master.start_new_role()

    configuration.save()

    configuration.expect_name_rejected()
    configuration.close()


def test_predefined_role_cannot_be_deleted(user_master: UserMasterPage) -> None:
    user_master.open_roles()

    user_master.ask_to_delete_role(PREDEFINED_ROLE)

    user_master.expect_message(PREDEFINED_REFUSAL)


def test_predefined_role_cannot_be_edited(user_master: UserMasterPage) -> None:
    user_master.open_roles()

    user_master.edit_role(PREDEFINED_ROLE)

    user_master.expect_message(PREDEFINED_REFUSAL)


def test_edit_icon_opens_the_role_of_its_own_row(saved_role: RoleSpec, user_master: UserMasterPage) -> None:
    """UR-09: the icon is clicked on an unselected row; live the app refuses as for a predefined role."""
    user_master.open_roles()

    configuration = user_master.click_edit_icon(saved_role.name)

    configuration.expect_shows(saved_role.name, saved_role.description)
