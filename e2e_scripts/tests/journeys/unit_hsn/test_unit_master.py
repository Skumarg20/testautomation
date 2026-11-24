"""J26: units and their UQC in Master > Inventory Master > Unit (specs/unit-uqc-hsn-rate-masters.md)."""

import re

import pytest

from pages.masters.master_toasts import MasterToasts
from pages.unit_hsn.master_lists import UnitList
from pages.unit_hsn.unit_form import UnitForm
from pages.unit_hsn.unit_hsn_records import UnitHsnRecords
from test_data.unit_hsn import PIECES_UQC, PREDEFINED_UNIT, UNIT_NAME_LENGTH

pytestmark = [pytest.mark.p2, pytest.mark.journey("unit-uqc-hsn-rate-masters")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
ALREADY_EXISTS = re.compile(r"Unit Already Exists", re.IGNORECASE)
PREDEFINED_NOT_DELETABLE = re.compile(r"Pre-Defined Unit Can't Be Deleted", re.IGNORECASE)
OVERLONG_SUFFIX = "XYZ"


def test_new_unit_is_listed_with_its_uqc(records: UnitHsnRecords, unit_list: UnitList) -> None:
    """Fails on the QA tenant 2026-10-09: the UQC cell stays empty for new units (defect D3 in the spec)."""
    unit = records.saved_unit()
    unit_list.open()
    unit_list.expect_uqc(unit.name, unit.uqc)


def test_saved_unit_keeps_its_uqc(records: UnitHsnRecords, unit_form: UnitForm) -> None:
    unit = records.saved_unit()
    unit_form.open_existing(unit.name)
    unit_form.expect_uqc(unit.uqc)


def test_unit_without_name_is_not_saved(unit_form: UnitForm) -> None:
    unit_form.open_new()
    unit_form.save()
    unit_form.expect_name_required()
    unit_form.expect_still_creating()


def test_duplicate_unit_name_is_refused(records: UnitHsnRecords, unit_form: UnitForm) -> None:
    unit = records.saved_unit()
    unit_form.open_new()
    unit_form.enter_name(unit.name)
    unit_form.save()
    MasterToasts(unit_form.page).expect_warning_saying(ALREADY_EXISTS)
    unit_form.expect_still_creating()


def test_duplicate_unit_check_ignores_letter_case(records: UnitHsnRecords, unit_form: UnitForm) -> None:
    unit = records.saved_unit()
    lower_case_twin = unit.name.lower()
    records.own_unit_name(lower_case_twin)
    unit_form.open_new()
    unit_form.enter_name(lower_case_twin)
    unit_form.save()
    MasterToasts(unit_form.page).expect_warning_saying(ALREADY_EXISTS)


def test_unit_name_is_cut_to_ten_characters(
    records: UnitHsnRecords, unit_form: UnitForm, unit_list: UnitList
) -> None:
    kept_name = records.new_unit_name()
    assert len(kept_name) == UNIT_NAME_LENGTH
    unit_form.open_new()
    unit_form.enter_name(kept_name + OVERLONG_SUFFIX)
    unit_form.save()
    unit_form.expect_saved()
    unit_list.open()
    unit_list.expect_listed(kept_name)


def test_renamed_unit_replaces_old_name_in_list(
    records: UnitHsnRecords, unit_form: UnitForm, unit_list: UnitList
) -> None:
    unit = records.saved_unit()
    new_name = records.new_unit_name()
    unit_form.open_existing(unit.name)
    unit_form.enter_name(new_name)
    unit_form.update()
    unit_form.expect_updated()
    unit_list.open()
    unit_list.expect_listed(new_name)
    unit_list.expect_not_listed(unit.name)


def test_changed_uqc_is_kept(records: UnitHsnRecords, unit_form: UnitForm) -> None:
    unit = records.saved_unit()
    unit_form.open_existing(unit.name)
    unit_form.choose_uqc(PIECES_UQC)
    unit_form.update()
    unit_form.expect_updated()
    unit_form.open_existing(unit.name)
    unit_form.expect_uqc(PIECES_UQC)


def test_predefined_unit_cannot_be_deleted(unit_list: UnitList) -> None:
    unit_list.open()
    unit_list.ask_to_delete(PREDEFINED_UNIT)
    MasterToasts(unit_list.page).expect_warning_saying(PREDEFINED_NOT_DELETABLE)


def test_unused_unit_is_deleted(records: UnitHsnRecords, unit_list: UnitList) -> None:
    unit = records.saved_unit()
    unit_list.open()
    unit_list.delete(unit.name)
    unit_list.expect_not_listed(unit.name)
