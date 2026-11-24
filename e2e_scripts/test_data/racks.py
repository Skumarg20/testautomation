"""Test-owned stores (warehouses) and racks for J28 rack-warehouse-management."""

from dataclasses import dataclass, replace
from itertools import count

# Predefined store of every company, seen live 2026-10-09 (specs/rack-warehouse-management.md).
MAIN_STORE = "Main Store"
STORE_CODE_RUN_CHARS = 4


@dataclass(frozen=True)
class StoreSpec:
    """Store Code and Store Name are both mandatory on the Create Store form."""

    code: str
    name: str

    def renamed(self, name: str) -> "StoreSpec":
        return replace(self, name=name)


@dataclass(frozen=True)
class RackSpec:
    name: str
    store: str

    def moved(self, name: str, store: str) -> "RackSpec":
        return replace(self, name=name, store=store)


class RackDataFactory:
    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._serial = count(1)

    def store(self) -> StoreSpec:
        serial = next(self._serial)
        code = f"Q{self._run_id[:STORE_CODE_RUN_CHARS]}{serial}"
        return StoreSpec(code=code, name=f"QA-{self._run_id}-St{serial}")

    def rack(self, store: str) -> RackSpec:
        return RackSpec(name=f"QA-{self._run_id}-R{next(self._serial)}", store=store)
