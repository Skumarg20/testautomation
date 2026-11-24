"""J40 Material Master: saving a BOM, its list row, the duplicate and empty-BOM checks, deleting it.

Scenario ids are those of scenarios/manufacturing-module.md; the plan is specs/manufacturing-module.md.
"""

import re

import pytest

from pages.manufacturing.bom_master import BomMasterForm, BomMasterList
from pages.stock.messages import StockMessages
from test_data.manufacturing import BomSpec, ManufacturingData, StockItem

# The fixtures switch a tenant-wide Control Room option on and back (spec N1).
pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = re.compile(r"^1(\.0+)?$")
ZERO = re.compile(r"^0(\.0+)?$")
NAME_ALREADY_EXISTS = re.compile(r"already exist", re.IGNORECASE)
RAW_MATERIAL_REQUIRED = re.compile(r"Raw Material Required!")


def test_saved_bom_returns_to_the_list(bom_list: BomMasterList, pack_bom_removed_afterwards: BomSpec) -> None:
    """MF-02: "Record saved successfully." and back on /transaction/billofmaterial."""
    bom_list.open()
    bom_list.create()
    form = BomMasterForm(bom_list.page)
    form.fill(pack_bom_removed_afterwards)
    form.save()
    form.expect_saved()


def test_bom_list_shows_the_saved_bom(bom_list: BomMasterList, saved_bom: BomSpec) -> None:
    """MF-03: BOM Name, Produced Item, Qty 1 and By Product Qty 0."""
    bom_list.open()
    bom_list.expect_listed(saved_bom)
    assert ONE.match(bom_list.quantity_of(saved_bom.name))
    assert ZERO.match(bom_list.by_product_quantity_of(saved_bom.name))


def test_bom_name_differing_only_by_case_and_spaces_is_refused(
    bom_list: BomMasterList, saved_bom: BomSpec, other_finished_item: StockItem
) -> None:
    """MF-07: the name check ignores case and spaces (BomMaterDAL.cs:259-263)."""
    lookalike = ManufacturingData.same_name_other_case(saved_bom, other_finished_item.spec)
    bom_list.open()
    bom_list.create()
    form = BomMasterForm(bom_list.page)
    form.fill(lookalike)
    form.save()
    # The duplicate shows as the field's validation text "BOM Name already exists !", not a toast
    # (billofmaterialmaster.ts:113-118, validation.component.html:39-40).
    form.expect_field_message(NAME_ALREADY_EXISTS)


def test_second_bom_for_the_same_finished_item_is_refused(
    bom_list: BomMasterList, saved_bom: BomSpec
) -> None:
    """MF-08: "Bom Of this <FG> Already Exists!" as soon as the finished item is chosen."""
    bom_list.open()
    bom_list.create()
    BomMasterForm(bom_list.page).enter_header(saved_bom)
    already_exists = re.compile(rf"Bom Of this {re.escape(saved_bom.finished.product)} Already Exists!")
    StockMessages(bom_list.page).expect_shown(already_exists)


def test_bom_without_raw_materials_is_not_saved(
    bom_list: BomMasterList, pack_bom_removed_afterwards: BomSpec
) -> None:
    """MF-09: "Raw Material Required!" and the editor stays open."""
    bom_list.open()
    bom_list.create()
    form = BomMasterForm(bom_list.page)
    form.fill(ManufacturingData.without_raw_materials(pack_bom_removed_afterwards))
    form.save()
    form.expect_refused(RAW_MATERIAL_REQUIRED)


def test_unused_bom_can_be_deleted(bom_list: BomMasterList, saved_bom: BomSpec) -> None:
    """MF-23: Yes on the confirmation removes the row (the toast says "updated", pack K3)."""
    bom_list.open()
    bom_list.delete(saved_bom.name)
    bom_list.expect_deleted()
    bom_list.expect_not_listed(saved_bom.name)
