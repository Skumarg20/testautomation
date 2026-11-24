import json
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.framework

MATRIX_FILE = Path("coverage/journey-matrix.json")
JOURNEY_MARKER = re.compile(r'pytest\.mark\.journey\("([^"]+)"\)')


def matrix_journeys() -> dict[str, dict[str, Any]]:
    return {journey["id"]: journey for journey in json.loads(MATRIX_FILE.read_text())["journeys"]}


def test_every_journey_marker_used_in_tests_exists_in_the_matrix() -> None:
    used = {
        m
        for path in Path("tests/journeys").rglob("test_*.py")
        for m in JOURNEY_MARKER.findall(path.read_text())
    }

    assert used <= set(matrix_journeys())


def test_every_spec_listed_in_the_matrix_exists() -> None:
    listed = [spec for journey in matrix_journeys().values() for spec in journey["specs"]]

    assert [spec for spec in listed if not Path(spec).exists()] == []


def test_matrix_has_41_journeys_with_unique_refs_and_slug_ids() -> None:
    journeys = json.loads(MATRIX_FILE.read_text())["journeys"]

    assert [journey["ref"] for journey in journeys] == [f"J{n:02d}" for n in range(1, 42)]
    assert len({journey["id"] for journey in journeys}) == 41


def test_priority_counts_match_the_workbook() -> None:
    priorities = [journey["priority"] for journey in matrix_journeys().values()]

    assert {p: priorities.count(p) for p in ("P0", "P1", "P2", "P3")} == {
        "P0": 6,
        "P1": 14,
        "P2": 14,
        "P3": 7,
    }


def passing_journeys_without_marked_specs(journeys: dict[str, dict[str, Any]]) -> list[str]:
    """Ids of `passing` journeys that list no spec carrying their journey marker.

    Who may promote, and on which run, is enforced by the console API (rule 1);
    the matrix stores no reviewer data. Offline we can only check that a passing
    journey has tests that a passed run for it could have come from.
    """
    unbacked = []
    for journey_id, journey in journeys.items():
        if journey["status"] != "passing":
            continue
        marked = [
            spec
            for spec in journey["specs"]
            if Path(spec).exists() and journey_id in JOURNEY_MARKER.findall(Path(spec).read_text())
        ]
        if not marked:
            unbacked.append(journey_id)
    return unbacked


def test_a_reviewed_passing_journey_with_marked_specs_is_accepted() -> None:
    journeys = {"auth": {"status": "passing", "specs": ["tests/journeys/auth/test_login.py"]}}

    assert passing_journeys_without_marked_specs(journeys) == []


def test_a_passing_journey_without_marked_specs_is_reported() -> None:
    journeys = {
        "no-specs": {"status": "passing", "specs": []},
        "wrong-marker": {"status": "passing", "specs": ["tests/journeys/auth/test_login.py"]},
        "generated": {"status": "generated", "specs": []},
    }

    assert passing_journeys_without_marked_specs(journeys) == ["no-specs", "wrong-marker"]


def test_every_passing_journey_has_specs_marked_with_it() -> None:
    assert passing_journeys_without_marked_specs(matrix_journeys()) == []


def test_every_journey_has_plan_flag_and_target_day() -> None:
    for journey in matrix_journeys().values():
        assert journey["in30Plan"] in {"yes", "stretch", "no", "phase2"}
        assert (journey["targetDay"] is None) == (journey["in30Plan"] == "phase2")
