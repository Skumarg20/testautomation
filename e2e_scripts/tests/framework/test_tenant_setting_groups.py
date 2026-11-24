"""Readers of a tenant-wide setting share the xdist group of the tests that change it (e2e/CLAUDE.md rule 0).

test_sales_gst_discount.py switches the garments GST type and bill-discount fields. Any journey that asserts
on-screen bill tax (it uses BillTotals) reads those settings, so it must run on the same worker.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.framework

TENANT_GROUP = 'pytest.mark.xdist_group("chemist-tenant")'


def bill_tax_readers(journeys: Path) -> list[Path]:
    return sorted(
        path
        for path in journeys.rglob("test_*.py")
        if "zz_probe_" not in str(path) and "totals: BillTotals" in path.read_text()
    )


def test_there_are_bill_tax_readers_to_check() -> None:
    assert bill_tax_readers(Path("tests/journeys"))


def test_every_bill_tax_reader_runs_on_the_tenant_settings_worker() -> None:
    readers = bill_tax_readers(Path("tests/journeys"))
    ungrouped = [str(path) for path in readers if TENANT_GROUP not in path.read_text()]

    assert ungrouped == []
