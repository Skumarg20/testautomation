"""J40 Material Master beyond the basic save: by-product and addition cost (MF-04), changing a saved BOM
(MF-25) and the BOM list of another company (MF-35)."""

import re
from collections.abc import Callable
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.manufacturing.bom_grids import BomGrid, BomGrids
from pages.manufacturing.bom_master import BomMasterForm, BomMasterList
from test_data.manufacturing import (
    ADDITIONAL_COST,
    SETS_ISSUED,
    BomSpec,
    ManufacturingData,
    StockItem,
)

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

Receive = Callable[[Decimal], None]
ONE_PRODUCT = "Total: 1 Product"
ONE_LEDGER = "Total: 1 Ledger"
ONE = re.compile(r"^1(\.0+)?$")
ALREADY_USED = re.compile(r"Bill of Material Already Used")
CHANGED_RM_A_PER_SET = Decimal(3)


def _fill_with_by_product_and_cost(form: BomMasterForm, bom: BomSpec) -> None:
    grids = BomGrids(form.page)
    form.fill(bom)
    grids.move_to_next_grid()
    grids.add_by_product(0, bom.by_products[0])
    grids.move_to_next_grid()
    grids.add_first_addition_ledger(ADDITIONAL_COST)


def test_by_product_and_addition_cost_are_counted_in_their_grid_totals(
    pack_bom_removed_afterwards: BomSpec, by_product_item: StockItem, bom_editor: BomMasterForm
) -> None:
    """MF-04: the footers read "Total: 1 Product" and "Total: 1 Ledger" (billofmaterialmaster.ts:820-829)."""
    bom = ManufacturingData.with_by_product(pack_bom_removed_afterwards, by_product_item.spec)
    _fill_with_by_product_and_cost(bom_editor, bom)
    grids = BomGrids(bom_editor.page)
    grids.expect_total(BomGrid.BY_PRODUCTS, ONE_PRODUCT)
    grids.expect_total(BomGrid.ADDITION_COST, ONE_LEDGER)


def test_bom_with_by_product_and_addition_cost_is_saved_with_its_by_product_quantity(
    pack_bom_removed_afterwards: BomSpec,
    by_product_item: StockItem,
    bom_editor: BomMasterForm,
) -> None:
    """MF-04: saved, and the list's By Product Qty reads 1."""
    bom = ManufacturingData.with_by_product(pack_bom_removed_afterwards, by_product_item.spec)
    _fill_with_by_product_and_cost(bom_editor, bom)
    bom_editor.save()
    bom_editor.expect_saved()
    bom_list = BomMasterList(bom_editor.page)
    bom_list.open()
    assert ONE.match(bom_list.by_product_quantity_of(bom.name))


def test_saved_bom_opens_for_change_with_its_raw_materials(
    bom_list: BomMasterList, saved_bom: BomSpec
) -> None:
    """MF-25 / MBC-16368: the item grid is filled when a saved BOM is opened for change."""
    bom_list.open()
    bom_list.edit(saved_bom.name)
    form = BomMasterForm(bom_list.page)
    for row, component in enumerate(saved_bom.raw_materials):
        form.expect_raw_material_listed(row, component.item.product)


def test_unused_bom_raw_quantity_change_is_updated(bom_list: BomMasterList, saved_bom: BomSpec) -> None:
    """MF-25: changing RM-A's quantity on an unused BOM answers "Record updated successfully."."""
    bom_list.open()
    bom_list.edit(saved_bom.name)
    form = BomMasterForm(bom_list.page)
    form.change_raw_quantity(0, CHANGED_RM_A_PER_SET)
    form.update()
    form.expect_updated()


def test_raw_row_of_a_used_bom_cannot_be_deleted(
    receive: Receive, bom_list: BomMasterList, saved_bom: BomSpec
) -> None:
    """MF-25: once the BOM has a receive, deleting a raw row gives "Bill of Material Already Used"
    (billofmaterialmaster.ts:836-839)."""
    receive(SETS_ISSUED)
    bom_list.open()
    bom_list.edit(saved_bom.name)
    grids = BomGrids(bom_list.page)
    grids.delete_row(BomGrid.RAW_MATERIALS, 0)
    grids.expect_message(ALREADY_USED)


def test_bom_of_one_company_is_not_listed_in_another(in_second_company: Page, saved_bom: BomSpec) -> None:
    """MF-35: the BOM list is filtered by company (BomMaterDAL.cs:38, `where bm.complinkid =`)."""
    bom_list = BomMasterList(in_second_company)
    bom_list.open_by_url()
    bom_list.expect_not_listed(saved_bom.name)
