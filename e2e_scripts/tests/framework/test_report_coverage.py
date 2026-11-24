import json
from pathlib import Path

import pytest

from scripts.report_coverage import (
    Journey,
    Matrix,
    build_summary,
    percent_passing,
    read_last_run,
    read_test_results,
    target_passing,
)

pytestmark = pytest.mark.framework

PAYMENT_NODE_ID = "tests/journeys/accounting/test_payment.py::test_payment[chromium-PM-002]@t"


def journey(priority: str, status: str) -> Journey:
    return Journey.model_validate(
        {
            "id": f"{priority}-{status}",
            "ref": "J00",
            "name": "n",
            "priority": priority,
            "layers": [],
            "in30Plan": "yes",
            "targetDay": None,
            "status": status,
            "specs": [],
        }
    )


def test_coverage_is_the_share_of_passing_journeys() -> None:
    journeys = [
        journey("P0", "passing"),
        journey("P0", "planned"),
        journey("P1", "passing"),
        journey("P2", "generated"),
    ]

    assert percent_passing(journeys) == 50


def test_coverage_of_an_empty_matrix_is_zero() -> None:
    assert percent_passing([]) == 0


def test_summary_counts_passing_journeys_per_priority() -> None:
    matrix = Matrix(
        version=1, journeys=[journey("P0", "passing"), journey("P0", "planned"), journey("P1", "planned")]
    )

    summary = build_summary(matrix, last_run=None, test_results=[])

    assert summary["byPriority"]["P0"] == {"total": 2, "passing": 1}
    assert summary["byPriority"]["P1"] == {"total": 1, "passing": 0}
    assert summary["byPriority"]["P2"] == {"total": 0, "passing": 0}
    assert summary["byPriority"]["P3"] == {"total": 0, "passing": 0}


def test_summary_counts_p3_journeys() -> None:
    matrix = Matrix(version=1, journeys=[journey("P3", "planned"), journey("P3", "passing")])

    assert build_summary(matrix, last_run=None, test_results=[])["byPriority"]["P3"] == {
        "total": 2,
        "passing": 1,
    }


def test_thirty_percent_target_of_41_journeys_is_13() -> None:
    assert target_passing(41) == 13


def test_summary_exposes_the_target_and_progress_towards_it() -> None:
    journeys = [journey("P0", "passing")] + [journey("P1", "planned") for _ in range(9)]

    summary = build_summary(Matrix(version=1, journeys=journeys), last_run=None, test_results=[])

    assert (summary["targetPassing"], summary["targetPct"]) == (3, 33)


def test_last_run_is_none_when_no_report_exists(tmp_path: Path) -> None:
    assert read_last_run(tmp_path / "missing.json") is None


def test_last_run_reads_pytest_json_report_counts(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"summary": {"passed": 5, "failed": 1, "error": 2, "skipped": 3}}))

    assert read_last_run(report) == {"passed": 5, "failed": 3, "skipped": 3}


def test_test_results_list_each_test_with_its_area_and_outcome(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "nodeid": PAYMENT_NODE_ID,
                        "outcome": "passed",
                    },
                    {"nodeid": "tests/journeys/auth/test_login.py::test_logout", "outcome": "failed"},
                ]
            }
        )
    )

    assert read_test_results(report) == [
        {"area": "accounting", "name": "test_payment[chromium-PM-002]", "outcome": "passed"},
        {"area": "auth", "name": "test_logout", "outcome": "failed"},
    ]


def test_test_results_are_empty_without_a_report(tmp_path: Path) -> None:
    assert read_test_results(tmp_path / "missing.json") == []
