"""J26: a new unit and HSN code in use by an item master, and the delete refusal while in use.

Plan: specs/unit-uqc-hsn-rate-masters.md (UH-U1 to UH-U3).
"""

import re

import pytest

from pages.inventory.item_list_page import UNIT, ItemListPage
from pages.masters.master_toasts import MasterToasts
from pages.unit_hsn.master_lists import HsnList, UnitList
from pages.unit_hsn.unit_hsn_records import UnitHsnRecords

pytestmark = [pytest.mark.p2, pytest.mark.journey("unit-uqc-hsn-rate-masters")]

# Case-blind; the app's own wording, including the missing space in "ItemAre", seen live 2026-10-09.
ITEMS_USE_UNIT = re.compile(r"Item\s?Are Available For This Unit", re.IGNORECASE)
ITEMS_USE_HSN = re.compile(r"Item\s?Are Available For This Hsn", re.IGNORECASE)
HSN_TAX_INFO = "HSN/SAC"


def test_item_is_saved_with_new_unit_and_hsn_code(records: UnitHsnRecords, item_list: ItemListPage) -> None:
    unit = records.saved_unit()
    hsn = records.saved_hsn()
    item = records.saved_item_using(unit, hsn)
    item_list.open()
    item_list.select(item.product)
    assert item_list.cell_text(item.product, UNIT) == unit.name
    assert item_list.tax_info(HSN_TAX_INFO) == hsn.code


def test_unit_used_by_an_item_cannot_be_deleted(records: UnitHsnRecords, unit_list: UnitList) -> None:
    unit = records.saved_unit()
    records.saved_item_using(unit, records.saved_hsn())
    unit_list.open()
    unit_list.ask_to_delete(unit.name)
    unit_list.confirm_delete()
    MasterToasts(unit_list.page).expect_error_saying(ITEMS_USE_UNIT)
    unit_list.expect_listed(unit.name)


def test_hsn_code_used_by_an_item_cannot_be_deleted(records: UnitHsnRecords, hsn_list: HsnList) -> None:
    hsn = records.saved_hsn()
    records.saved_item_using(records.saved_unit(), hsn)
    hsn_list.open()
    hsn_list.ask_to_delete(hsn.code)
    hsn_list.confirm_delete()
    MasterToasts(hsn_list.page).expect_error_saying(ITEMS_USE_HSN)
    hsn_list.expect_listed(hsn.code)
