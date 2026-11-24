"""Unit names and HSN codes from one factory never repeat; past the field's room the factory says so."""

import pytest

from test_data.unit_hsn import HSN_CODE_LENGTH, UNIT_NAME_LENGTH, UnitHsnDataFactory

pytestmark = pytest.mark.framework

RUN_ID = "a1b2c3d4"


def test_unit_names_stay_unique_and_fit_the_field_for_36_units() -> None:
    factory = UnitHsnDataFactory(RUN_ID)
    names = [factory.unit_name() for _ in range(36)]

    assert len(set(names)) == 36
    assert all(len(name) == UNIT_NAME_LENGTH for name in names)


def test_hsn_codes_stay_unique_digits_for_ten_codes() -> None:
    factory = UnitHsnDataFactory(RUN_ID)
    codes = [factory.hsn().code for _ in range(10)]

    assert len(set(codes)) == 10
    assert all(code.isdigit() and len(code) == HSN_CODE_LENGTH for code in codes)


def test_a_repeat_raises_instead_of_making_a_duplicate() -> None:
    factory = UnitHsnDataFactory(RUN_ID)
    for _ in range(10):
        factory.hsn()

    with pytest.raises(ValueError, match="HSN"):
        factory.hsn()
