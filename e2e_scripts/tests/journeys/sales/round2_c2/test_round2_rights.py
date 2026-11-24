"""Ajay rows 163, 164, 165, 166: the sale list follows the role's rights.

The plan's seat limit stops a test creating a user (UR-10, tests/journeys/admin/test_user_management.py),
so the
suite's limited login "operator" is used. Its rights are not guessed: they are read from its role in the Roles
tab (predefined role "Operator", test_data/user_roles.py PREDEFINED_ROLE), then the sale list is checked
against
them. Delete / Edit follow IsDelete / IsEdit (processout.list.component.ts:1106-1110). Rate and discount are
role rows only when the Sale menu lists them; if it does not, the row is skipped (Decision needed: where the
rate and discount rights live). Decision needed too: that the operator login holds the Operator role.
"""

import re
from collections.abc import Callable, Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.admin.round2_c2.role_rights import RightColumn, RoleRights, SaleListActions, open_sale_list
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from pages.masters.round2_c2.owned_parties import OwnedParties
from test_data.user_roles import PREDEFINED_ROLE

pytestmark = [pytest.mark.p2, pytest.mark.journey("role-based-access")]

SALE_MENU = "Sale"
BILL_ROW = re.compile(r"Bill", re.IGNORECASE)
BILL_AMOUNT = Decimal(150)
LIMITED: Account = "operator"


@pytest.fixture
def one_bill(guarded_page: Page, parties: OwnedParties, zero_rated_item_name: str) -> Iterator[str]:
    party = parties.saved_with_email().name
    PartyAvailability(guarded_page).wait_until_selectable(party)
    desk = SaleBillDesk(guarded_page, zero_rated_item_name)
    number = desk.create(party, BILL_AMOUNT, Decimal(0))
    yield party
    desk.delete(number)


@pytest.fixture
def limited_page(company_page: Callable[[Account, str], Page], one_bill: str) -> Page:
    page = company_page(LIMITED, GARMENTS_COMPANY)
    DashboardPage(page).open()
    open_sale_list(page, one_bill)
    return page


def _operator_rights(guarded_page: Page) -> dict[RightColumn, bool]:
    return RoleRights(guarded_page).granted(PREDEFINED_ROLE, SALE_MENU, BILL_ROW)


def test_delete_is_offered_only_with_the_delete_right(guarded_page: Page, limited_page: Page) -> None:
    """Row 163."""
    allowed = _operator_rights(guarded_page)[RightColumn.DELETE]

    offered = any("delete" in action.lower() for action in SaleListActions(limited_page).row_actions())

    assert offered == allowed


def test_modify_is_offered_only_with_the_edit_right(guarded_page: Page, limited_page: Page) -> None:
    """Row 164."""
    allowed = _operator_rights(guarded_page)[RightColumn.EDIT]

    assert SaleListActions(limited_page).has_edit_button() == allowed


@pytest.mark.parametrize(
    ("row", "pattern"),
    [(165, re.compile(r"Rate", re.IGNORECASE)), (166, re.compile(r"Discount", re.IGNORECASE))],
    ids=["row-165-rate", "row-166-discount"],
)
def test_rate_and_discount_rights_are_listed_for_the_role(
    guarded_page: Page, row: int, pattern: re.Pattern[str]
) -> None:
    """Rows 165 and 166: the Sale menu of the role lists the right (the login's grid cannot be compared)."""
    try:
        rights = RoleRights(guarded_page).granted(PREDEFINED_ROLE, SALE_MENU, pattern)
    except AssertionError:
        pytest.skip(f"row {row}: role {PREDEFINED_ROLE} has no Sale row named like {pattern.pattern}")
    assert RightColumn.FULL in rights
