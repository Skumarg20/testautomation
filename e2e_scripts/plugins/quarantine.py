"""Quarantine hook (F07 6.4, requirements R21 and R22).

Reads `quarantine.json` next to the pytest rootdir and marks each listed test
`xfail(run=True, strict=False, reason="quarantined: <defect>")`, so it keeps running, a failure does not
fail the build, and a pass is reported as `xpassed`.

File format (written by the console API, approved entries only): a JSON list of objects

    [{"nodeid": "tests/x/test_a.py::test_one", "defect": "D-001", "reviewBy": "2026-10-20"}]

`nodeid` is relative to `e2e/`. An entry without parameters matches every parametrised case and browser
(`nodeid == entry` or `nodeid` starts with `entry + "["`). Extra keys are ignored.

Failure behaviour is fail open to gating, never to hiding: a missing, unreadable or invalid file, or a
non-list root, quarantines nothing and prints one warning; an invalid entry (no `nodeid`, no `defect`,
no ISO `reviewBy`) is skipped with a warning. An entry matching no collected test is reported. An overdue
entry (today in UTC is after `reviewBy`) still applies, and the run header prints `REVIEW OVERDUE`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

QUARANTINE_FILE = "quarantine.json"
_STASH: pytest.StashKey[QuarantineState] = pytest.StashKey()


@dataclass(frozen=True)
class Entry:
    nodeid: str
    defect: str
    review_by: date


@dataclass
class QuarantineState:
    entries: list[Entry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_entry(raw: Any) -> Entry | None:
    if not isinstance(raw, dict):
        return None
    nodeid, defect, review_by = raw.get("nodeid"), raw.get("defect"), raw.get("reviewBy")
    if not (isinstance(nodeid, str) and nodeid.strip() and isinstance(defect, str) and defect.strip()):
        return None
    try:
        parsed = date.fromisoformat(str(review_by))
    except ValueError:
        return None
    return Entry(nodeid.strip(), defect.strip(), parsed)


def load_entries(path: Path) -> QuarantineState:
    """Never raises: any problem leaves the list empty (or skips one entry) and adds a warning."""
    state = QuarantineState()
    if not path.is_file():
        return state  # no file is the normal state; nothing is quarantined and nothing is printed
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        state.warnings.append(f"quarantine file {path.name} is unreadable, nothing is quarantined ({error})")
        return state
    if not isinstance(document, list):
        state.warnings.append(f"quarantine file {path.name} must hold a JSON list, nothing is quarantined")
        return state
    skipped = 0
    for raw in document:
        entry = _parse_entry(raw)
        if entry is None:
            skipped += 1
        else:
            state.entries.append(entry)
    if skipped:
        state.warnings.append(f"quarantine file {path.name}: skipped {skipped} invalid entry(ies)")
    return state


def matches(entry_nodeid: str, item_nodeid: str) -> bool:
    return item_nodeid == entry_nodeid or item_nodeid.startswith(entry_nodeid + "[")


def pytest_configure(config: pytest.Config) -> None:
    try:
        state = load_entries(Path(str(config.rootpath)) / QUARANTINE_FILE)
    except Exception as error:  # noqa: BLE001 - fail open: a broken hook must never stop the run
        state = QuarantineState(warnings=[f"quarantine hook failed, nothing is quarantined ({error!r})"])
    config.stash[_STASH] = state


def pytest_report_header(config: pytest.Config) -> list[str]:
    state = config.stash.get(_STASH, None)
    if state is None:
        return []
    today = _today()
    lines = [
        f"REVIEW OVERDUE: {e.nodeid} {e.defect} since {e.review_by.isoformat()}"
        for e in state.entries
        if today > e.review_by
    ]
    if state.entries:
        lines.insert(0, f"quarantine: {len(state.entries)} entry(ies) from {QUARANTINE_FILE}")
    return lines


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    state = config.stash.get(_STASH, None)
    if state is None or not state.entries:
        return
    for entry in state.entries:
        hit = [item for item in items if matches(entry.nodeid, item.nodeid)]
        if not hit:
            state.notes.append(f"quarantine entry matches no test: {entry.nodeid}")
        for item in hit:
            item.add_marker(pytest.mark.xfail(run=True, strict=False, reason=f"quarantined: {entry.defect}"))


def pytest_terminal_summary(terminalreporter: Any, config: pytest.Config) -> None:
    state = config.stash.get(_STASH, None)
    if state is None or not (state.warnings or state.notes):
        return
    terminalreporter.section("quarantine")
    for line in [*state.warnings, *state.notes]:
        terminalreporter.write_line(f"WARNING {line}" if line in state.warnings else line)
