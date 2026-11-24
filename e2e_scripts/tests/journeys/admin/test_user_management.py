"""J15 user management: the plan's user limit stops a new invitation before any message is sent.

Plan: specs/user-role-management.md (UR-10). Creating, editing, deactivating or deleting a user is not
automated (NEEDS DECISION UR-D1, UR-D2).
"""

import pytest

from pages.admin.user_master_page import UserMasterPage

pytestmark = [pytest.mark.p1, pytest.mark.journey("user-role-management")]


def test_invite_beyond_the_user_limit_names_the_limit(user_master: UserMasterPage) -> None:
    """Live the plan allows as many users as are listed, so the invite form never opens."""
    user_master.open_users()
    listed_users = user_master.user_count()

    user_master.invite_user()

    user_master.expect_seat_limit_alert(listed_users)
