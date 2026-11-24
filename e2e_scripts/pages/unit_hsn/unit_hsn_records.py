"""Test-owned units, HSN codes and items: made through the UI, remembered, and deleted in teardown."""

from collections.abc import Callable
from dataclasses import replace

from playwright.sync_api import Page

from pages.components.owned_records import deletion_steps
from pages.components.undo import UndoStep, undo_all
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.unit_hsn.hsn_form import HsnForm
from pages.unit_hsn.master_lists import HsnList, UnitList
from pages.unit_hsn.unit_form import UnitForm
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec
from test_data.unit_hsn import HsnSpec, UnitHsnDataFactory, UnitSpec


class UnitHsnRecords:
    """Every record is remembered before the UI is asked to save it, so a half-done save is cleaned too."""

    def __init__(self, page: Page, run_id: str) -> None:
        self._page = page
        self._run_id = run_id
        self._data = UnitHsnDataFactory(run_id)
        self._units: list[str] = []
        self._hsn_codes: list[str] = []
        self._items: list[str] = []

    def new_unit(self) -> UnitSpec:
        unit = self._data.unit()
        self.own_unit_name(unit.name)
        return unit

    def new_unit_name(self) -> str:
        name = self._data.unit_name()
        self.own_unit_name(name)
        return name

    def new_hsn(self) -> HsnSpec:
        hsn = self._data.hsn()
        self.own_hsn_code(hsn.code)
        return hsn

    def own_unit_name(self, name: str) -> None:
        self._units.append(name)

    def own_hsn_code(self, code: str) -> None:
        self._hsn_codes.append(code)

    def saved_unit(self) -> UnitSpec:
        unit = self.new_unit()
        form = UnitForm(self._page)
        form.open_new()
        form.enter(unit)
        form.save()
        form.expect_saved()
        return unit

    def saved_hsn(self) -> HsnSpec:
        hsn = self.new_hsn()
        form = HsnForm(self._page)
        form.open_new()
        form.enter(hsn)
        form.save()
        form.expect_saved()
        return hsn

    def saved_item_using(self, unit: UnitSpec, hsn: HsnSpec) -> ItemMasterSpec:
        """An item with only the mandatory fields, measured in this unit and filed under this HSN code."""
        item = replace(DataFactory(self._run_id).item_master(), unit=unit.name, hsn=hsn.code)
        self._items.append(item.product)
        form = CreateItemPage(self._page)
        form.open()
        form.fill(item)
        form.save()
        form.expect_saved()
        form.decline_opening_stock()
        return item

    def delete_all(self) -> None:
        """Items go first: a unit or HSN code that an item uses cannot be deleted. Every delete runs; the
        failures are reported together at the end."""
        undo_all(
            [
                *self._item_deletion_steps(),
                *deletion_steps("unit", UnitList(self._page), self._units),
                *deletion_steps("HSN code", HsnList(self._page), self._hsn_codes),
            ]
        )

    def _item_deletion_steps(self) -> list[UndoStep]:
        if not self._items:
            return []
        items = ItemListPage(self._page)
        return [
            ("item list", items.open),
            *((f"item {product}", _item_deleter(items, product)) for product in self._items),
        ]


def _item_deleter(items: ItemListPage, product: str) -> Callable[[], None]:
    def delete() -> None:
        if items.has_item(product):
            items.delete(product)

    return delete
