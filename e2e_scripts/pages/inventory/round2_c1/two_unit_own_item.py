"""An own, stocked item that then gets a second unit worth 10 pieces, with Multi Unit held on.

Order matters: stock is bought while the item has one unit (the purchase screen then takes plain quantities);
Multi Unit is switched on afterwards and the item edited to add the unit (Create Item form, `#btnMultiUnit`).
On exit the settings are put back first, then the purchase bill and the item are deleted (own_stocked_item).
"""

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.round2_c1.item_deal import ItemDealForm
from pages.inventory.round2_c1.own_item import OwnItem, own_stocked_item
from pages.inventory.round2_c1.two_unit_item import give_second_unit
from pages.settings.round2_c1.multi_unit_settings import TWO_UNITS, MultiUnitSettings, multi_unit_held

PIECES_PER_BIGGER_UNIT = 10


@contextmanager
def two_unit_own_item(page: Page, run_id: str) -> Iterator[OwnItem]:
    with own_stocked_item(page, run_id) as item:
        DashboardPage(page).open()
        with multi_unit_held(MultiUnitSettings(page), TWO_UNITS):
            form = ItemDealForm(page)
            form.open_item(item.code)
            give_second_unit(CreateItemPage(page), PIECES_PER_BIGGER_UNIT)
            form.update()
            yield item
            DashboardPage(page).open()
