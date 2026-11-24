"""Bundles of what a round-2 C1 sale case works with, so a test takes two fixtures, not seven."""

from contextlib import AbstractContextManager
from dataclasses import dataclass

from pages.masters.round2_c1.scheme_master import SchemeApi, scheme_created
from pages.masters.round2_c1.scheme_payload import Criteria, SchemeItem, SchemeSpec, SchemeType, Slab
from pages.sale.manual.option_settings import HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.manual.saved_bills import SavedBills
from pages.sale.round2_c1.cells import GridCells


@dataclass
class Desk:
    """The bill, its cells, the held settings and the saved bills."""

    bill: PharmaBill
    cells: GridCells
    options: HeldOptions
    saved: SavedBills


@dataclass
class SchemeKit:
    api: SchemeApi
    item: SchemeItem
    run_id: str

    def spec(self, label: str, shape: tuple[SchemeType, Criteria], slab: Slab) -> SchemeSpec:
        kind, criteria = shape
        return SchemeSpec(f"QA-{self.run_id}-{label}", kind, criteria, (slab,))

    def created(self, spec: SchemeSpec, item: SchemeItem | None = None) -> AbstractContextManager[int]:
        return scheme_created(self.api, spec, item or self.item)
