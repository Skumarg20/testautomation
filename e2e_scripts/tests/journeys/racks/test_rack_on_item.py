"""J28: a rack picked on an item, and the delete rule for a rack in use (specs/rack-warehouse-management.md).

These tests switch Control Room "Rack Master" to Yes and back, so they share the tenant group (rule 0).
"""

import pytest
from playwright.sync_api import Page

from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.racks.item_rack import ItemRackField
from pages.racks.rack_master import RackList
from test_data.models import ItemMasterSpec
from test_data.racks import RackSpec

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("rack-warehouse-management"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def test_rack_picked_on_item_is_kept_on_the_item(
    item_on_rack: tuple[ItemMasterSpec, RackSpec], rack_field_page: Page
) -> None:
    item, rack = item_on_rack
    items = ItemListPage(rack_field_page)
    items.open()
    items.edit(item.product)
    CreateItemPage(rack_field_page).expect_editing(item.product)
    ItemRackField(rack_field_page).expect_value(rack.name)


def test_rack_used_by_an_item_cannot_be_deleted(
    item_on_rack: tuple[ItemMasterSpec, RackSpec], rack_list: RackList
) -> None:
    _, rack = item_on_rack
    rack_list.open()
    rack_list.try_to_delete(rack.name)
    rack_list.open()
    rack_list.expect_listed(rack.name)
