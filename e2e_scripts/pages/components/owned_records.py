"""Teardown of the records a test made on master list screens (stores, racks, units, HSN codes).

Every delete runs even when an earlier one fails, and the failures are reported together at the end (see
`pages.components.undo`), so one refused delete does not leave every later record on the shared tenant.
"""

from collections.abc import Callable, Iterable
from typing import Protocol

from pages.components.undo import UndoStep

DELETE_ATTEMPTS = 3


class ListedRecords(Protocol):
    """A list screen that can be opened, searched for a record and asked to delete it."""

    def open(self) -> None: ...

    def is_listed(self, name: str) -> bool: ...

    def delete(self, name: str) -> None: ...


class RecordStillListedError(AssertionError):
    def __init__(self, name: str) -> None:
        super().__init__(f'"{name}" is still listed after {DELETE_ATTEMPTS} deletes')


def deletion_steps(label: str, screen: ListedRecords, names: Iterable[str]) -> list[UndoStep]:
    """Undo steps for `undo_all`: open the list once, then delete each record named."""
    names = list(names)
    if not names:
        return []
    opening: UndoStep = (f"{label} list", screen.open)
    return [opening, *((f"{label} {name}", _deleter(screen, name)) for name in names)]


def _deleter(screen: ListedRecords, name: str) -> Callable[[], None]:
    return lambda: delete_until_gone(screen, name)


def delete_until_gone(screen: ListedRecords, name: str) -> None:
    """Deletes every copy of the record (a retried save can make two), but gives up instead of looping."""
    for _ in range(DELETE_ATTEMPTS):
        if not screen.is_listed(name):
            return
        screen.delete(name)
    if screen.is_listed(name):
        raise RecordStillListedError(name)
