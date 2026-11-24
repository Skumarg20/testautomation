"""Journey fixtures pin the company: a login opens in whichever company another suite used last."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.framework

JOURNEYS = Path("tests/journeys")
PINS_THE_COMPANY = ("company_page(", "ensure_company(")
# Suites whose data belongs to the licence, not to a company; their conftest says why.
COMPANY_FREE_SUITES = {"subscription"}


def suites_logging_in_without_a_company() -> list[str]:
    unpinned = []
    for conftest in sorted(JOURNEYS.glob("*/conftest.py")):
        suite = conftest.parent.name
        source = conftest.read_text()
        if suite in COMPANY_FREE_SUITES or "page_as(" not in source:
            continue
        if not any(pin in source for pin in PINS_THE_COMPANY):
            unpinned.append(suite)
    return unpinned


def test_every_journey_suite_that_logs_in_pins_its_company() -> None:
    assert suites_logging_in_without_a_company() == []
