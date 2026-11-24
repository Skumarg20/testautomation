"""Test-owned routes, areas and stations for J25 (specs/route-station-area-masters.md)."""

from dataclasses import dataclass
from itertools import count


@dataclass(frozen=True)
class AreaSpec:
    name: str
    route: str


class OtherMasterDataFactory:
    """Names are `QA-<run_id>-<label>-<n>`: 15 characters for a route or station, inside every limit seen."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._serial = count(1)

    def route(self) -> str:
        return self._unique_name("Rte")

    def station(self) -> str:
        return self._unique_name("Stn")

    def area(self, route: str) -> AreaSpec:
        return AreaSpec(self._unique_name("Area"), route)

    def _unique_name(self, label: str) -> str:
        return f"QA-{self._run_id}-{label}-{next(self._serial)}"
