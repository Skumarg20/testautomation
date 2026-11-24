"""J40 who reaches the manufacturing screens: a role without the "MaterialIssue" right (MF-34), and the
BMR Type master the KB places under Master > Inventory Master (MF-37)."""

import pytest
from playwright.sync_api import Page

from pages.components.access_denied import AccessDenied
from pages.manufacturing.menu import InventoryMasterMenu, ManufacturingMenu, ManufacturingScreen

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

MATERIAL_ISSUE_PATH = "/sale/matissue"
BMR_TYPE = "BMR Type"


def test_material_issue_is_not_in_the_menu_of_a_role_without_its_right(operator_page: Page) -> None:
    """MF-34: no "MaterialIssue" right under Stock Management (processout.list.component.ts:435), no entry."""
    ManufacturingMenu(operator_page).expect_screen_missing(ManufacturingScreen.MATERIAL_ISSUE)


def test_material_issue_url_is_refused_to_a_role_without_its_right(operator_page: Page) -> None:
    """MF-34: the direct URL redirects or shows a denial."""
    AccessDenied(operator_page).expect_denied(MATERIAL_ISSUE_PATH)


def test_bmr_type_master_is_listed_under_inventory_master(manufacturing_page: Page) -> None:
    """MF-37: KB `#a835ce0d` lists Master > Inventory Master > BMR Type. The Angular source imports its
    component from files that are not in the repo (manufacturing.module.ts:8-9, K1), so a failure here is
    the question N7 asks, not a locator fault."""
    InventoryMasterMenu(manufacturing_page).expect_entry(BMR_TYPE)
