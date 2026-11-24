"""J40 Material Master field checks: required header fields, the BOM Name length, raw-row checks, the item
pickers' refusals, the addition-cost amount and the finished item's conversion (MF-05, 06, 10-13).

Messages are the code's strings (scenarios/manufacturing-module.md); locators are unverified live.
"""

import re
from decimal import Decimal

import pytest

from pages.manufacturing.bom_grids import BomGrid, BomGrids
from pages.manufacturing.bom_master import BomMasterForm, BomMasterList, HeaderField
from pages.purchase.documents.selection_window import SelectionWindow
from test_data.manufacturing import (
    BOM_NAME_MAX_LENGTH,
    BOM_NAME_MIN_LENGTH,
    FINISHED_CONVERSION,
    BomSpec,
    ManufacturingData,
    StockItem,
)
from test_data.models import ItemMasterSpec

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

REQUIRED = {
    HeaderField.NAME: re.compile(r"BOM Name required !"),
    HeaderField.ITEM: re.compile(r"Item Name required !"),
    HeaderField.QUANTITY: re.compile(r"Quantity required !"),
}
TOO_SHORT = re.compile(r"Minimum \d+ characters required !")
SELECT_ITEM_FIRST = re.compile(r"Please select item first")
QUANTITY_ABOVE_ZERO = re.compile(r"Quantity should be greater than 0!")
SERVICE_REFUSED = re.compile(r"Can't Select Service Item!")
FINISHED_GOOD_REFUSED = re.compile(r"Can't Select Finised Good!")
RAW_MATERIAL_REFUSED = re.compile(r"Can't Select Raw Material Items!")
AMOUNT_REQUIRED = re.compile(r"Please enter amount")
NOT_A_MULTIPLE = re.compile(r"Quantity Should By multiple of conversion")
ONE_PRODUCT = "Total: 1 Product"
UNICODE_SUFFIX = "-ñé#&"
NOT_A_MULTIPLE_OF_TEN = FINISHED_CONVERSION + 5
ZERO_QUANTITY = Decimal(0)
NO_COST = Decimal(0)
TEN = re.compile(r"^10(\.0+)?$")


@pytest.mark.parametrize("field", list(HeaderField), ids=lambda field: field.name.lower())
def test_blank_header_field_is_marked_required(bom_editor: BomMasterForm, field: HeaderField) -> None:
    """MF-05: bomname, itemname and qty are required (billofmaterialmaster.ts:126-128)."""
    bom_editor.leave_blank(field)
    bom_editor.expect_field_message(REQUIRED[field])


def test_bom_name_input_stops_at_fifty_characters(
    bom_editor: BomMasterForm, mf_data: ManufacturingData
) -> None:
    """MF-06: maxlength 50, so a 51st character cannot be typed."""
    bom_editor.type_name(mf_data.name_of_length(BOM_NAME_MAX_LENGTH + 1))
    assert len(bom_editor.name_typed()) == BOM_NAME_MAX_LENGTH


def test_bom_name_of_three_characters_is_marked_too_short(
    bom_editor: BomMasterForm, mf_data: ManufacturingData
) -> None:
    """MF-06: minlength 4 on the input (billofmaterialmaster.html:26)."""
    bom_editor.type_name(mf_data.name_of_length(BOM_NAME_MIN_LENGTH - 1))
    bom_editor.leave_name()
    bom_editor.expect_field_message(TOO_SHORT)


def test_bom_name_of_four_characters_is_not_marked_too_short(
    bom_editor: BomMasterForm, mf_data: ManufacturingData
) -> None:
    """MF-06: four characters is the shortest name the input accepts."""
    bom_editor.type_name(mf_data.name_of_length(BOM_NAME_MIN_LENGTH))
    bom_editor.leave_name()
    bom_editor.expect_no_field_message(TOO_SHORT)


def test_bom_name_keeps_unicode_and_special_characters(
    bom_editor: BomMasterForm, mf_data: ManufacturingData
) -> None:
    """MF-06: the BOM Name input has no input mask, so what is typed stays (pack: UNVERIFIED, see N5)."""
    name = mf_data.name_of_length(BOM_NAME_MIN_LENGTH) + UNICODE_SUFFIX
    bom_editor.type_name(name)
    assert bom_editor.name_typed() == name


def test_quantity_on_a_raw_row_without_an_item_is_refused(
    pack_bom: BomSpec, bom_editor: BomMasterForm
) -> None:
    """MF-10: "Please select item first" (MB-036277 said it was missing; fixed)."""
    bom_grids = BomGrids(bom_editor.page)
    bom_editor.enter_header(pack_bom)
    SelectionWindow(bom_editor.page).close_without_choosing()
    bom_grids.enter_quantity(BomGrid.RAW_MATERIALS, 0, pack_bom.raw_materials[0].quantity_per_set)
    bom_grids.expect_message(SELECT_ITEM_FIRST)


def test_raw_material_quantity_of_zero_is_refused(pack_bom: BomSpec, bom_editor: BomMasterForm) -> None:
    """MF-10: "Quantity should be greater than 0!"."""
    bom_grids = BomGrids(bom_editor.page)
    bom_editor.enter_header(pack_bom)
    bom_grids.start_raw_row(0)
    SelectionWindow(bom_editor.page).choose_cell_text(pack_bom.raw_materials[0].item.product)
    bom_grids.enter_quantity(BomGrid.RAW_MATERIALS, 0, ZERO_QUANTITY)
    bom_grids.expect_message(QUANTITY_ABOVE_ZERO)


def test_service_item_is_refused_as_raw_material(
    pack_bom: BomSpec, service_item: ItemMasterSpec, bom_editor: BomMasterForm
) -> None:
    """MF-11: "Can't Select Service Item!" (itemmaster.component.ts:4891-4894)."""
    bom_grids = BomGrids(bom_editor.page)
    bom_editor.enter_header(pack_bom)
    bom_grids.start_raw_row(0)
    bom_grids.offer_item(service_item.product)
    bom_grids.expect_message(SERVICE_REFUSED)


def test_finished_item_is_refused_as_its_own_raw_material(
    pack_bom: BomSpec, bom_editor: BomMasterForm
) -> None:
    """MF-11: "Can't Select Finised Good!" (spelled so in global.ts:19739)."""
    bom_grids = BomGrids(bom_editor.page)
    bom_editor.enter_header(pack_bom)
    bom_grids.start_raw_row(0)
    bom_grids.offer_item(pack_bom.finished.product)
    bom_grids.expect_message(FINISHED_GOOD_REFUSED)


def test_raw_material_is_refused_as_a_by_product(pack_bom: BomSpec, bom_editor: BomMasterForm) -> None:
    """MF-11: a by-product may not be one of the BOM's raw materials (itemmaster.component.ts:4896-4899)."""
    bom_grids = BomGrids(bom_editor.page)
    raw_a = pack_bom.raw_materials[0]
    bom_editor.enter_header(pack_bom)
    bom_editor.add_raw_material(0, raw_a)
    bom_grids.move_to_next_grid()
    bom_grids.offer_item(raw_a.item.product)
    bom_grids.expect_message(RAW_MATERIAL_REFUSED)


def test_raw_material_chosen_twice_stays_one_row(pack_bom: BomSpec, bom_editor: BomMasterForm) -> None:
    """MF-11: picking RM-A again moves to its row instead of adding a second (bom.itemselection.ts:111)."""
    bom_grids = BomGrids(bom_editor.page)
    raw_a = pack_bom.raw_materials[0]
    bom_editor.enter_header(pack_bom)
    bom_editor.add_raw_material(0, raw_a)
    bom_grids.start_raw_row(1)
    bom_grids.offer_item(raw_a.item.product)
    bom_grids.expect_total(BomGrid.RAW_MATERIALS, ONE_PRODUCT)


def test_addition_cost_of_zero_is_refused(
    pack_bom: BomSpec, by_product_item: StockItem, bom_editor: BomMasterForm
) -> None:
    """MF-12: "Please enter amount" for a ledger row with no cost."""
    bom_grids = BomGrids(bom_editor.page)
    bom = ManufacturingData.with_by_product(pack_bom, by_product_item.spec)
    bom_editor.fill(bom)
    bom_grids.move_to_next_grid()
    bom_grids.add_by_product(0, bom.by_products[0])
    bom_grids.move_to_next_grid()
    bom_grids.add_first_addition_ledger(NO_COST)
    bom_grids.expect_message(AMOUNT_REQUIRED)


def test_tab_on_quantity_warns_about_the_conversion(bom_in_tens: BomSpec, bom_editor: BomMasterForm) -> None:
    """MF-13 / K6: Tab on Qty gives "Quantity Should By multiple of conversion" (the condition ends in
    `|| event.keyCode == KeyEnum.Tab`, billofmaterialmaster.ts:447)."""
    bom_grids = BomGrids(bom_editor.page)
    bom_editor.type_name(bom_in_tens.name)
    bom_editor.choose_item(bom_in_tens.finished.product)
    bom_editor.type_quantity(NOT_A_MULTIPLE_OF_TEN)
    bom_editor.press_tab_on_quantity()
    bom_grids.expect_message(NOT_A_MULTIPLE)


def test_bom_quantity_is_saved_times_the_conversion(
    bom_in_tens: BomSpec, bom_editor: BomMasterForm, bom_list: BomMasterList
) -> None:
    """MF-13: Qty 1 of an item with Conversion 10 is saved as 10 (billofmaterialmaster.ts:698)."""
    bom_editor.fill(bom_in_tens)
    bom_editor.save()
    bom_editor.expect_saved()
    bom_list.open()
    assert TEN.match(bom_list.quantity_of(bom_in_tens.name))
