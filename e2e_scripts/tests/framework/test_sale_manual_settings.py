"""The sale-bill setting helpers of the manual cases: option matching, hold and restore, number patterns."""

from decimal import Decimal
from typing import cast

import pytest

from pages.sale.manual.option_settings import (
    ZERO_RATE,
    HeldOptions,
    OptionNotOfferedError,
    OptionNotRestoredError,
    SaleBillSettings,
    SettingField,
    index_of_option,
    same_text,
    setting_held,
)
from pages.sale.manual.pharma_bill import whole_number_text

pytestmark = pytest.mark.framework

OFFERED = ["Indicate on Item and Bill", "Indicate on Item", "No"]


class FakeSettings:
    """Stands in for the Setting window: one value per field id; `sticky` ignores writes after the first."""

    def __init__(self, value: str) -> None:
        self.value = value
        self.writes: list[str] = []
        self.sticky = False

    def current(self, field: SettingField) -> str:
        assert field == ZERO_RATE
        return self.value

    def choose(self, field: SettingField, wanted: str) -> None:
        assert field == ZERO_RATE
        self.writes.append(wanted)
        if not (self.sticky and len(self.writes) > 1):
            self.value = wanted


def as_settings(fake: FakeSettings) -> SaleBillSettings:
    return cast(SaleBillSettings, fake)


@pytest.mark.parametrize(
    ("wanted", "index"),
    [("No", 2), ("indicate on item", 1), ("Indicate on Item and Bill", 0)],
)
def test_option_is_found_by_whole_text_first(wanted: str, index: int) -> None:
    assert index_of_option("Zero rate", wanted, OFFERED) == index


def test_option_is_found_by_a_unique_partial_text() -> None:
    assert index_of_option("Zero rate", "and bill", OFFERED) == 0


@pytest.mark.parametrize("wanted", ["Indicate", "Ask"])
def test_ambiguous_or_missing_option_is_an_error_naming_what_is_offered(wanted: str) -> None:
    with pytest.raises(OptionNotOfferedError, match="Indicate on Item"):
        index_of_option("Zero rate", wanted, OFFERED)


def test_same_text_ignores_case_and_edges() -> None:
    assert same_text(" Yes ", "yes")
    assert not same_text("Yes", "No")


def test_field_is_set_inside_and_restored_after() -> None:
    fake = FakeSettings("No")
    with setting_held(as_settings(fake), ZERO_RATE, "Indicate on Item") as original:
        assert (original, fake.value) == ("No", "Indicate on Item")
    assert fake.value == "No"


def test_field_at_the_wanted_value_is_never_written() -> None:
    fake = FakeSettings("No")
    with setting_held(as_settings(fake), ZERO_RATE, "no"):
        pass
    assert fake.writes == []


def test_field_is_restored_when_the_test_fails() -> None:
    fake = FakeSettings("No")
    with pytest.raises(RuntimeError), setting_held(as_settings(fake), ZERO_RATE, "Indicate on Item"):
        raise RuntimeError("test failed")
    assert fake.value == "No"


def test_a_restore_that_did_not_take_is_an_error() -> None:
    fake = FakeSettings("No")
    fake.sticky = True
    with (
        pytest.raises(OptionNotRestoredError, match='it was "No"'),
        setting_held(as_settings(fake), ZERO_RATE, "Indicate on Item"),
    ):
        fake.sticky = True


def test_held_options_open_and_close_a_bill_around_every_change() -> None:
    fake = FakeSettings("No")
    calls: list[str] = []
    held = HeldOptions(as_settings(fake), lambda: calls.append("open"), lambda: calls.append("close"))

    held.hold(ZERO_RATE, "Indicate on Item")
    held.close()

    assert calls == ["open", "close", "open", "close"]
    assert fake.value == "No"


def test_held_options_that_held_nothing_open_no_bill() -> None:
    calls: list[str] = []
    held = HeldOptions(as_settings(FakeSettings("No")), lambda: calls.append("open"), lambda: None)

    held.close()

    assert calls == []


@pytest.mark.parametrize("text", ["3", "3.000", " 3.00 "])
def test_whole_number_pattern_accepts_the_grids_formats(text: str) -> None:
    assert whole_number_text(Decimal(3)).fullmatch(text)


def test_whole_number_pattern_takes_thousands_commas_and_refuses_other_numbers() -> None:
    pattern = whole_number_text(Decimal(99999))
    assert pattern.fullmatch("99,999.00")
    assert pattern.fullmatch("99999")
    assert not pattern.fullmatch("9,999")
    assert not whole_number_text(Decimal(3)).fullmatch("13")
