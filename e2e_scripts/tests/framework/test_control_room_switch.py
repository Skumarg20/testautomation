"""switch_held: a tenant-wide Control Room switch is read first, changed only if needed, always restored."""

import pytest

from pages.settings.control_room import YesNo
from pages.settings.control_room_switch import SwitchNotRestoredError, SwitchValue, switch_held

pytestmark = pytest.mark.framework

BOM = "Bill Of Material(BOM)"
BOM_ON = SwitchValue(BOM, "Yes")


class FakeControlRoom:
    """Records writes; `sticky` keeps the value from changing back, like a save that did not take."""

    def __init__(self, value: YesNo) -> None:
        self.value: YesNo = value
        self.writes: list[YesNo] = []
        self.sticky = False

    def current_switch(self, name: str) -> YesNo:
        assert name == BOM
        return self.value

    def set_switch(self, name: str, value: YesNo) -> None:
        assert name == BOM
        self.writes.append(value)
        if not (self.sticky and self.writes[:-1]):
            self.value = value


def test_switch_is_on_inside_and_back_to_the_original_after() -> None:
    room = FakeControlRoom("No")
    with switch_held(room, BOM_ON) as original:
        assert (original, room.value) == ("No", "Yes")
    assert room.value == "No"


def test_switch_already_at_the_wanted_value_is_never_written() -> None:
    room = FakeControlRoom("Yes")
    with switch_held(room, BOM_ON):
        pass
    assert room.writes == []


def test_switch_is_restored_when_the_test_fails() -> None:
    room = FakeControlRoom("No")
    with pytest.raises(RuntimeError), switch_held(room, BOM_ON):
        raise RuntimeError("test failed")
    assert room.value == "No"


def test_switch_is_restored_when_the_clean_up_before_it_fails() -> None:
    room = FakeControlRoom("No")

    def broken_clean_up() -> None:
        raise RuntimeError("dashboard did not open")

    with pytest.raises(RuntimeError), switch_held(room, BOM_ON, broken_clean_up):
        pass
    assert room.value == "No"


def test_clean_up_runs_before_the_restore() -> None:
    room = FakeControlRoom("No")
    seen_during_clean_up: list[YesNo] = []
    with switch_held(room, BOM_ON, lambda: seen_during_clean_up.append(room.value)):
        pass
    assert seen_during_clean_up == ["Yes"]


def test_a_switch_that_does_not_go_back_is_an_error() -> None:
    room = FakeControlRoom("No")
    room.sticky = True
    with pytest.raises(SwitchNotRestoredError, match="put it back by hand"), switch_held(room, BOM_ON):
        pass


def test_switch_is_restored_when_switching_it_on_fails_half_way() -> None:
    room = FakeControlRoom("No")
    original_set = room.set_switch

    def save_then_time_out(name: str, value: YesNo) -> None:
        original_set(name, value)
        if value == "Yes":
            raise TimeoutError("confirm dialog did not close")

    room.set_switch = save_then_time_out  # type: ignore[method-assign]
    with pytest.raises(TimeoutError), switch_held(room, BOM_ON):
        pass
    assert room.value == "No"
