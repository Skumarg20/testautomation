"""J36: the CRM group of the sidebar on the garments company (specs/crm-module.md, CRM-01)."""

import pytest

from pages.crm.crm_menu import CrmMenu

pytestmark = [pytest.mark.p3, pytest.mark.journey("crm-module")]

GARMENTS_CRM_ENTRIES = ("Loyalty Management System", "Pending Approvals")


def test_crm_group_lists_loyalty_and_pending_approvals(crm_menu: CrmMenu) -> None:
    crm_menu.expect_entries(GARMENTS_CRM_ENTRIES)
