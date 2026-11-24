"""Test-owned roles for the user and role management journey (J15 `user-role-management`)."""

from dataclasses import dataclass

# Seen on the garments QA tenant 2026-10-08 (specs/user-role-management.md); tests never change them.
PREDEFINED_ROLE = "Operator"
DASHBOARD_MENU = "Dashboard"
MASTER_MENU = "Master"
NET_SALE_RIGHT = "Net Sale"
LEDGER_MASTER_RIGHT = "Ledger Master"


@dataclass(frozen=True)
class Right:
    """One row of the Role Configurations grid: a screen (`name`) under a left-hand `menu`."""

    menu: str
    name: str


@dataclass(frozen=True)
class RoleSpec:
    name: str
    description: str
    right: Right


def new_role(run_id: str) -> RoleSpec:
    """A role owned by one test: its name carries the run id so teardown deletes only what the test made."""
    return RoleSpec(
        name=f"QA-{run_id}-Role",
        description=f"QA role {run_id}",
        right=Right(DASHBOARD_MENU, NET_SALE_RIGHT),
    )
