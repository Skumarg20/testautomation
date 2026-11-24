"""Builds results/module-report/index.html: tests grouped by module, with status, reason and recordings.

Reads results/report.json (the last pytest run) and results/recordings/ (a run made with QA_RECORD=1).
"""

import json
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from fixtures.session import recording_folder_for

REPORT_FILE = Path("results/report.json")
RECORDINGS_ROOT = Path("results/recordings")
OUTPUT_FILE = Path("results/module-report/index.html")
MODULE_PARENT = "journeys"
OTHER_MODULE = "other"
PHASES = ("setup", "call", "teardown")
SKIP_PREFIX = re.compile(r"Skipped: (.*?)'\)?$", re.DOTALL)
VIDEO_SUFFIX = ".webm"
RUN_COMMAND = 'QA_RECORD=1 .venv/bin/python -m pytest "{target}" --headed --slowmo 250'
STYLE = (
    "body{font:14px system-ui;margin:24px;background:#f6f7f8;color:#1c1f23}"
    "details{background:#fff;border:1px solid #d9dde1;border-radius:6px;margin:8px 0;padding:8px 12px}"
    "summary{cursor:pointer}.passed{color:#13795b}.failed,.error{color:#c62828}.skipped{color:#9a6700}"
    "code{background:#eef0f2;padding:2px 5px;border-radius:4px;word-break:break-all}"
    "video{max-width:100%;margin-top:8px}img{max-width:100%;border:1px solid #d9dde1}"
)


@dataclass
class TestRow:
    nodeid: str
    outcome: str
    seconds: float
    reason: str
    recordings: list[Path] = field(default_factory=list)


@dataclass
class Module:
    name: str
    tests: list[TestRow] = field(default_factory=list)

    def count(self, outcome: str) -> int:
        return sum(1 for test in self.tests if test.outcome == outcome)


def build_modules(entries: list[dict[str, Any]], recordings_root: Path) -> list[Module]:
    modules: dict[str, Module] = {}
    for entry in entries:
        module = modules.setdefault(_module_name(entry["nodeid"]), Module(_module_name(entry["nodeid"])))
        module.tests.append(_row(entry, recordings_root))
    return sorted(modules.values(), key=lambda module: module.name)


def _module_name(nodeid: str) -> str:
    parts = nodeid.split("::")[0].split("/")
    return parts[parts.index(MODULE_PARENT) + 1] if MODULE_PARENT in parts[:-1] else OTHER_MODULE


def _row(entry: dict[str, Any], recordings_root: Path) -> TestRow:
    seconds = sum(float(entry.get(phase, {}).get("duration", 0)) for phase in PHASES)
    return TestRow(
        entry["nodeid"],
        entry["outcome"],
        seconds,
        _reason(entry),
        _recordings(entry["nodeid"], recordings_root),
    )


def _reason(entry: dict[str, Any]) -> str:
    for phase in PHASES:
        outcome = entry.get(phase, {})
        if outcome.get("outcome") == "skipped":
            return _skip_reason(str(outcome.get("longrepr", "")))
        crash = outcome.get("crash")
        if crash:
            return str(crash.get("message", ""))
    return ""


def _skip_reason(longrepr: str) -> str:
    match = SKIP_PREFIX.search(longrepr)
    return match.group(1) if match else longrepr


def _recordings(nodeid: str, recordings_root: Path) -> list[Path]:
    folder = recording_folder_for(recordings_root, nodeid)
    return sorted(folder.iterdir()) if folder.is_dir() else []


def render_html(modules: list[Module]) -> str:
    body = "".join(_module_html(module) for module in modules)
    return f"<!doctype html><meta charset=utf-8><title>Module report</title><style>{STYLE}</style>{body}"


def _module_html(module: Module) -> str:
    counts = " · ".join(f"{module.count(o)} {o}" for o in ("passed", "failed", "skipped") if module.count(o))
    command = escape(RUN_COMMAND.format(target=f"tests/journeys/{module.name}"))
    tests = "".join(_test_html(test) for test in module.tests)
    heading = f"<h2>{escape(module.name)} <small>{counts}</small></h2>"
    return f"{heading}<p>Run module: <code>{command}</code></p>{tests}"


def _test_html(test: TestRow) -> str:
    title = escape(test.nodeid.split("::", 1)[-1])
    reason = f"<p><b>Why:</b> {escape(test.reason)}</p>" if test.reason else ""
    command = escape(RUN_COMMAND.format(target=test.nodeid))
    return (
        f"<details><summary><b class={test.outcome}>{test.outcome.upper()}</b> {title} "
        f"<small>({test.seconds:.1f}s)</small></summary>{reason}<p>Run: <code>{command}</code></p>"
        f"{_media_html(test.recordings)}</details>"
    )


def _media_html(recordings: list[Path]) -> str:
    return "".join(_media_item(path) for path in recordings)


def _media_item(path: Path) -> str:
    source = escape(Path("..", "recordings", path.parent.name, path.name).as_posix())
    if path.suffix == VIDEO_SUFFIX:
        return f'<video controls preload="none" src="{source}"></video>'
    return f'<p><a href="{source}"><img loading="lazy" src="{source}" alt="final screen"></a></p>'


def write_report() -> Path:
    entries = json.loads(REPORT_FILE.read_text())["tests"]
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(render_html(build_modules(entries, RECORDINGS_ROOT)))
    return OUTPUT_FILE


if __name__ == "__main__":
    print(write_report())
