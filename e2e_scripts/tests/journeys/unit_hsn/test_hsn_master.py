"""J26: HSN/SAC codes in Master > Inventory Master > HSN / SAC (specs/unit-uqc-hsn-rate-masters.md)."""

import pytest

from pages.unit_hsn.hsn_form import HsnForm
from pages.unit_hsn.master_lists import HsnList
from pages.unit_hsn.unit_hsn_records import UnitHsnRecords
from test_data.unit_hsn import HSN_CODE_LENGTH

pytestmark = [pytest.mark.p2, pytest.mark.journey("unit-uqc-hsn-rate-masters")]

OVERLONG_DIGITS = "12"
# HSN codes are numeric (KB careportal_enriched_v5.csv#27613ae1); letters fail e-way bills (#514affd4).
LETTERS_IN_CODE = "ABCD"


def test_new_hsn_code_is_listed_with_its_name(records: UnitHsnRecords, hsn_list: HsnList) -> None:
    hsn = records.saved_hsn()
    hsn_list.open()
    hsn_list.expect_name(hsn.code, hsn.name)


def test_hsn_code_is_cut_to_eight_digits(
    records: UnitHsnRecords, hsn_form: HsnForm, hsn_list: HsnList
) -> None:
    hsn = records.new_hsn()
    assert len(hsn.code) == HSN_CODE_LENGTH
    hsn_form.open_new()
    hsn_form.enter_code(hsn.code + OVERLONG_DIGITS)
    hsn_form.enter_name(hsn.name)
    hsn_form.save()
    hsn_form.expect_saved()
    hsn_list.open()
    hsn_list.expect_name(hsn.code, hsn.name)


def test_hsn_code_with_letters_is_refused(
    records: UnitHsnRecords, hsn_form: HsnForm, hsn_list: HsnList
) -> None:
    """Fails on the QA tenant 2026-10-09: the code is saved (defect, see the spec's NEEDS DECISION 3)."""
    hsn = records.new_hsn()
    code_with_letters = LETTERS_IN_CODE + hsn.code[len(LETTERS_IN_CODE) :]
    records.own_hsn_code(code_with_letters)
    hsn_form.open_new()
    hsn_form.enter_code(code_with_letters)
    hsn_form.enter_name(hsn.name)
    hsn_form.save()
    hsn_list.open()
    hsn_list.expect_not_listed(code_with_letters)


def test_hsn_without_code_is_not_saved(records: UnitHsnRecords, hsn_form: HsnForm, hsn_list: HsnList) -> None:
    """Fails on the QA tenant 2026-10-09: a record is saved (defect, see the spec's NEEDS DECISION 4)."""
    hsn = records.new_hsn()
    # Seen live: the name typed with the code empty lands in the code field, cut to 8 characters.
    name_as_code = hsn.name[:HSN_CODE_LENGTH]
    records.own_hsn_code(name_as_code)
    hsn_form.open_new()
    hsn_form.enter_name(hsn.name)
    hsn_form.save()
    hsn_list.open()
    hsn_list.expect_not_listed(name_as_code)


def test_renamed_hsn_code_is_listed_with_new_name(
    records: UnitHsnRecords, hsn_form: HsnForm, hsn_list: HsnList
) -> None:
    hsn = records.saved_hsn()
    new_name = f"{hsn.name}-Ren"
    hsn_form.open_existing(hsn.code)
    hsn_form.enter_name(new_name)
    hsn_form.update()
    hsn_form.expect_updated()
    hsn_list.open()
    hsn_list.expect_name(hsn.code, new_name)


def test_unused_hsn_code_is_deleted(records: UnitHsnRecords, hsn_list: HsnList) -> None:
    hsn = records.saved_hsn()
    hsn_list.open()
    hsn_list.delete(hsn.code)
    hsn_list.expect_not_listed(hsn.code)
