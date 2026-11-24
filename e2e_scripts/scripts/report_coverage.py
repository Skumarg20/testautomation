"""Builds ../dashboard/public/data/summary.json from the journey matrix and the last pytest run."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

Priority = Literal["P0", "P1", "P2", "P3"]
PRIORITIES: tuple[Priority, ...] = ("P0", "P1", "P2", "P3")
TARGET_FRACTION = 0.30
Plan = Literal["yes", "stretch", "no", "phase2"]
MATRIX_FILE = Path("coverage/journey-matrix.json")
PYTEST_REPORT_FILE = Path("results/report.json")
SUMMARY_FILE = Path("../dashboard/public/data/summary.json")


class Journey(BaseModel):
    id: str
    ref: str
    name: str
    priority: Priority
    layers: list[str]
    in30Plan: Plan  # noqa: N815 (JSON key is camelCase)
    targetDay: int | None  # noqa: N815
    status: Literal["not_started", "planned", "generated", "passing"]
    specs: list[str]

    @property
    def is_passing(self) -> bool:
        return self.status == "passing"


class Matrix(BaseModel):
    version: int
    journeys: list[Journey]


def count_passing(journeys: list[Journey]) -> int:
    return sum(journey.is_passing for journey in journeys)


def percent_passing(journeys: list[Journey]) -> int:
    return round(count_passing(journeys) / len(journeys) * 100) if journeys else 0


def target_passing(total: int) -> int:
    return math.ceil(total * TARGET_FRACTION)


def target_pct(passing: int, target: int) -> int:
    return round(passing / target * 100) if target else 0


def counts_by_priority(journeys: list[Journey]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for priority in PRIORITIES:
        matching = [journey for journey in journeys if journey.priority == priority]
        result[priority] = {"total": len(matching), "passing": count_passing(matching)}
    return result


def read_last_run(report_file: Path) -> dict[str, int] | None:
    if not report_file.exists():
        return None
    counts = json.loads(report_file.read_text()).get("summary", {})
    return {
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0) + counts.get("error", 0),
        "skipped": counts.get("skipped", 0),
    }


def read_test_results(report_file: Path) -> list[dict[str, str]]:
    """One row per test of the last run: the journey folder it lives in, its name and its outcome."""
    if not report_file.exists():
        return []
    return [_test_row(test) for test in json.loads(report_file.read_text()).get("tests", [])]


def _test_row(test: dict[str, Any]) -> dict[str, str]:
    path, _, name = test["nodeid"].partition("::")
    folders = Path(path).parts
    area = folders[2] if len(folders) > 3 and folders[1] == "journeys" else folders[1]
    return {"area": area, "name": name.split("@")[0], "outcome": test["outcome"]}


def build_summary(
    matrix: Matrix, last_run: dict[str, int] | None, test_results: list[dict[str, str]]
) -> dict[str, Any]:
    journeys = matrix.journeys
    target = target_passing(len(journeys))
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "functionalCoveragePct": percent_passing(journeys),
        "total": len(journeys),
        "passing": count_passing(journeys),
        "targetPassing": target,
        "targetPct": target_pct(count_passing(journeys), target),
        "byPriority": counts_by_priority(journeys),
        "journeys": [journey.model_dump() for journey in journeys],
        "lastRun": last_run,
        "tests": test_results,
    }


def main() -> None:
    matrix = Matrix.model_validate_json(MATRIX_FILE.read_text())
    summary = build_summary(matrix, read_last_run(PYTEST_REPORT_FILE), read_test_results(PYTEST_REPORT_FILE))
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    print(
        f"Functional coverage: {summary['functionalCoveragePct']}% "
        f"({summary['passing']}/{summary['total']}), "
        f"30% target: {summary['passing']}/{summary['targetPassing']}"
    )


if __name__ == "__main__":
    main()
