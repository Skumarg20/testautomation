"""Outstanding cases as pytest parameters: a case the workbook marks as a known app issue is an xfail."""

import pytest
from _pytest.mark.structures import ParameterSet

from test_data.outstanding_steps import OutstandingCase


def as_params(cases: tuple[OutstandingCase, ...]) -> list[ParameterSet]:
    return [pytest.param(case, id=case.id, marks=_marks(case)) for case in cases]


def _marks(case: OutstandingCase) -> list[pytest.MarkDecorator]:
    if case.known_issue:
        return [pytest.mark.xfail(reason=f"{case.id}: {case.known_issue}", strict=False)]
    return []
