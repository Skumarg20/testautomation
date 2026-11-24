"""Typed access to the imported phase-1 cases; produced by scripts/import_document_cases.py."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

CASES_FILE = Path(__file__).parent / "document_cases.json"
NEGATIVE = "NEGATIVE"


@dataclass(frozen=True)
class DocumentCase:
    id: str
    module: str
    sheet: str
    type: str
    description: str
    active: bool
    inputs: dict[str, str] = field(default_factory=dict)
    line_items: tuple[dict[str, str], ...] = ()

    @property
    def is_negative(self) -> bool:
        return self.type == NEGATIVE


@cache
def _all_cases() -> tuple[DocumentCase, ...]:
    records = json.loads(CASES_FILE.read_text())
    return tuple(DocumentCase(**{**r, "line_items": tuple(r["line_items"])}) for r in records)


def cases_for(module: str, sheet: str) -> list[DocumentCase]:
    """Active cases of one sheet, in file order; use as `pytest.mark.parametrize` input with `ids=case_id`."""
    return [c for c in _all_cases() if c.module == module and c.sheet == sheet and c.active]


def case_id(case: DocumentCase) -> str:
    return case.id
