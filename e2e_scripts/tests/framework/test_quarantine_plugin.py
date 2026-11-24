"""The quarantine hook (F07-R21, R22): xfail(run=True, strict=False) from quarantine.json, failing open."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
pytestmark = pytest.mark.framework

E2E_DIR = Path(__file__).resolve().parents[2]
TESTS = """
import pytest

def test_flaky():
    assert False, "boom"

def test_stable():
    assert True

@pytest.mark.parametrize("variant", ["chromium", "webkit"])
def test_param(variant):
    assert False

def test_recovered():
    assert True
"""


@pytest.fixture
def project(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    monkeypatch.setenv("PYTHONPATH", str(E2E_DIR))  # the subprocess imports plugins.quarantine from here
    pytester.makepyfile(test_sample=TESTS)
    return pytester


def run(project: pytest.Pytester, *args: str) -> pytest.RunResult:
    return project.runpytest_subprocess("-p", "plugins.quarantine", "-p", "no:cacheprovider", *args)


def write(project: pytest.Pytester, entries: object) -> None:
    project.makefile(".json", quarantine=json.dumps(entries) if not isinstance(entries, str) else entries)


def entry(nodeid: str, review_by: str | None = None) -> dict[str, str]:
    soon = (date.today() + timedelta(days=7)).isoformat()
    return {"nodeid": nodeid, "defect": "D-001", "reviewBy": review_by or soon}


def test_hook_xfails_listed_nodeid_with_defect_reason(project: pytest.Pytester) -> None:
    write(project, [entry("test_sample.py::test_flaky")])
    result = run(project, "-rx", "-k", "test_flaky or test_stable")
    result.assert_outcomes(passed=1, xfailed=1)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*quarantined: D-001*"])


def test_hook_matches_parametrised_cases(project: pytest.Pytester) -> None:
    write(project, [entry("test_sample.py::test_param")])
    result = run(project, "-k", "test_param")
    result.assert_outcomes(xfailed=2)
    assert result.ret == 0


def test_hook_xpass_does_not_fail_the_run(project: pytest.Pytester) -> None:
    write(project, [entry("test_sample.py::test_recovered")])
    result = run(project, "-k", "test_recovered")
    result.assert_outcomes(xpassed=1)
    assert result.ret == 0


def test_missing_file_is_inert(project: pytest.Pytester) -> None:
    result = run(project)
    result.assert_outcomes(passed=2, failed=3)
    assert "WARNING" not in result.stdout.str()
    assert "xfailed" not in result.stdout.str()


@pytest.mark.parametrize("content", ["{", '{"nodeid": "x"}', "null", ""])
def test_hook_missing_or_corrupt_file_quarantines_nothing_and_warns(
    project: pytest.Pytester, content: str
) -> None:
    write(project, content)
    result = run(project)
    result.assert_outcomes(passed=2, failed=3)
    assert result.stdout.str().count("WARNING quarantine file") == 1


def test_hook_skips_invalid_entry_and_warns(project: pytest.Pytester) -> None:
    write(project, [{"defect": "D-001", "reviewBy": "2026-12-01"}, entry("test_sample.py::test_flaky")])
    result = run(project, "-k", "test_flaky")
    result.assert_outcomes(xfailed=1)
    assert result.stdout.str().count("WARNING quarantine file") == 1


def test_entry_without_defect_is_skipped_so_the_test_still_gates(project: pytest.Pytester) -> None:
    write(project, [{"nodeid": "test_sample.py::test_flaky", "reviewBy": "2099-01-01"}])
    result = run(project, "-k", "test_flaky")
    result.assert_outcomes(failed=1)


def test_hook_overdue_entry_still_applies_and_prints_header(project: pytest.Pytester) -> None:
    write(project, [entry("test_sample.py::test_flaky", "2020-01-01")])
    result = run(project, "-k", "test_flaky")
    result.assert_outcomes(xfailed=1)
    result.stdout.fnmatch_lines(["*REVIEW OVERDUE: test_sample.py::test_flaky D-001 since 2020-01-01*"])


def test_entry_matching_no_test_is_reported(project: pytest.Pytester) -> None:
    write(project, [entry("test_sample.py::test_gone"), entry("test_sample.py::test_flaky")])
    result = run(project, "-k", "test_flaky")
    result.assert_outcomes(xfailed=1)
    result.stdout.fnmatch_lines(["*quarantine entry matches no test: test_sample.py::test_gone*"])


def test_prefix_does_not_match_a_longer_function_name(project: pytest.Pytester) -> None:
    write(project, [entry("test_sample.py::test_flak")])
    result = run(project, "-k", "test_flaky")
    result.assert_outcomes(failed=1)
