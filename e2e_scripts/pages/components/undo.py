"""Teardown that undoes every record a test made, even when undoing one of them fails.

A plain loop stops at the first failed delete and leaves every later record on the shared QA tenant. Here
each step runs, and the failures are reported together at the end, named by the record they left behind.
"""

from collections.abc import Callable, Iterable

from playwright.sync_api import Error as PlaywrightError

UndoStep = tuple[str, Callable[[], None]]


class UndoIncompleteError(AssertionError):
    def __init__(self, failures: list[str]) -> None:
        super().__init__("Teardown left records behind: " + "; ".join(failures))


def undo_all(steps: Iterable[UndoStep]) -> None:
    """Runs every (record name, undo) step in order; raises once at the end if any of them failed."""
    failures = [failure for name, undo in steps if (failure := _failure_of(name, undo))]
    if failures:
        raise UndoIncompleteError(failures)


def _failure_of(name: str, undo: Callable[[], None]) -> str:
    try:
        undo()
    except (AssertionError, PlaywrightError) as error:
        first_line = next(iter(str(error).strip().splitlines()), type(error).__name__)
        return f"{name}: {first_line}"
    return ""
