"""The zz_probe_* modules save records and assert nothing, so a normal run must not collect them."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.framework

PROBE_DIRS = sorted(Path("tests/journeys").glob("zz_probe_*"))


def collect(tmp_path: Path, *paths: str) -> str:
    reports = [
        f"--junitxml={tmp_path / 'junit.xml'}",
        f"--json-report-file={tmp_path / 'report.json'}",
        f"--html={tmp_path / 'report.html'}",
    ]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *reports, *paths],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr


def test_probe_packages_exist_for_this_check_to_mean_something() -> None:
    assert PROBE_DIRS


def test_a_journeys_run_does_not_collect_the_probe_modules(tmp_path: Path) -> None:
    out = collect(tmp_path, *(str(d) for d in PROBE_DIRS), "tests/journeys/racks")

    assert "zz_probe_" not in out
    assert "racks/" in out


def test_a_probe_can_still_be_run_by_naming_its_file(tmp_path: Path) -> None:
    probe = str(PROBE_DIRS[0] / "test_probe.py")

    assert "test_probe.py::" in collect(tmp_path, probe)
