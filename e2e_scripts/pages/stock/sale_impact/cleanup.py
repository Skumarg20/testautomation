"""Undo steps a test registers as it creates data, run last-in first-out even when the test failed."""

from collections.abc import Callable


class Cleanup:
    def __init__(self) -> None:
        self._steps: dict[str, Callable[[], None]] = {}

    def add(self, name: str, step: Callable[[], None]) -> None:
        self._steps[name] = step

    def discard(self, name: str) -> None:
        """For a document the test deleted itself: its undo step is no longer needed."""
        del self._steps[name]

    def run_all(self) -> None:
        """Every step runs; the first failure is raised once the rest have been tried."""
        failures: list[Exception] = []
        while self._steps:
            _, step = self._steps.popitem()
            try:
                step()
            except Exception as error:
                failures.append(error)
        if failures:
            raise failures[0]
