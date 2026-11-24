"""J40 the two Control Room switches: with each one on, Stock Management lists its screens (MF-01, MF-29).

The fixtures turn the switch on for the test and put the tenant's original value back (spec N1). The default
of No (KB `onedrive_processed_data.csv#de1c77aa`) is not asserted: another session may have changed it.
"""

import pytest
from playwright.sync_api import Page

from pages.manufacturing.menu import BILL_OF_MATERIALS, CONVERSION, ManufacturingMenu

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def test_bom_switch_lists_material_master_issue_and_received(bom_page: Page) -> None:
    """MF-01: "Bill Of Material(BOM)" = Yes shows Bill of Materials > Material Master, Issue, Received."""
    ManufacturingMenu(bom_page).expect_entries_under(BILL_OF_MATERIALS)


def test_conversion_switch_lists_one_to_many_and_many_to_one(conversion_page: Page) -> None:
    """MF-29: "One To Many & Many To One required?" = Yes shows Conversion > One to many, Many to one."""
    ManufacturingMenu(conversion_page).expect_entries_under(CONVERSION)
