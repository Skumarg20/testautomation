"""Holds a tenant-wide Control Room Yes/No switch at a value for one test and puts the original back.

The original is read first (never assumed), the switch is only written when it differs, and the restore runs
even when the test or the clean-up step before it fails. After the restore the value is read again: a switch
left in the wrong state is an error, not a warning, because every later suite on the tenant sees it.
Callers change a tenant-wide setting, so their tests run in xdist group "chemist-tenant" (CLAUDE.md rule 0).
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

from pages.settings.control_room import YesNo


class SwitchAccess(Protocol):
    def current_switch(self, name: str) -> YesNo: ...

    def set_switch(self, name: str, value: YesNo) -> None: ...


class SwitchNotRestoredError(AssertionError):
    def __init__(self, name: str, original: YesNo, now: YesNo) -> None:
        super().__init__(
            f'Control Room "{name}" is "{now}" after the restore, it was "{original}": put it back by hand'
        )


@dataclass(frozen=True)
class SwitchValue:
    """A Control Room option by its full Particulars text, and the value a test needs."""

    name: str
    wanted: YesNo


def _nothing_to_prepare() -> None:
    """The default clean-up before the restore."""


@contextmanager
def switch_held(
    access: SwitchAccess,
    switch: SwitchValue,
    before_restore: Callable[[], None] = _nothing_to_prepare,
) -> Iterator[YesNo]:
    """Yields the original value; `before_restore` gets the page to where the Control Room opens from."""
    original = access.current_switch(switch.name)
    if original == switch.wanted:
        yield original
        return
    try:
        # Inside the try: a save that fails half-way may still have changed the tenant.
        access.set_switch(switch.name, switch.wanted)
        yield original
    finally:
        _restore(access, SwitchValue(switch.name, original), before_restore)


def _restore(access: SwitchAccess, original: SwitchValue, before_restore: Callable[[], None]) -> None:
    try:
        before_restore()
    finally:
        access.set_switch(original.name, original.wanted)
    now = access.current_switch(original.name)
    if now != original.wanted:
        raise SwitchNotRestoredError(original.name, original.wanted, now)
