"""Live run events for the QA Console (F03 section 6.1).

Load with `python -m pytest -p plugins.console_events` from `e2e/`. The import works only through
`python -m pytest`, which puts the working directory on `sys.path`. The plugin is inert unless the env
variable CONSOLE_EVENTS_FILE names a file: without it no hook is registered and nothing is written.

One JSON object per line is appended to that file, flushed at once:
  collected  {"t","total","ts"}                      once, by the controller
  queued     {"t","nodeids":[...],"ts"}              the collected node ids, in chunks under 4 KB
  start      {"t","nodeid","worker","ts"}            one per attempt, by the process that runs the test
  end        {"t","nodeid","worker","outcome","durationMs","ts", "message"?, "setupError"?, "skipReason"?}
  log        {"t","level","source","message","nodeid"?,"ts"}
  session_end {"t","exitstatus","ts"}                once, by the controller

`outcome` is passed, failed, skipped, xfailed, xpassed, rerun (a failed attempt that will be retried) or
flaky (a pass after at least one rerun). With xdist the workers write start and end (xdist re-fires those
hooks in the controller, which skips them), except that the controller writes the failed end of a crashed
worker. Secret values listed in the file named by CONSOLE_SECRET_VALUES_FILE are masked before writing.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

import pytest

ENV_EVENTS_FILE = "CONSOLE_EVENTS_FILE"
ENV_SECRETS_FILE = "CONSOLE_SECRET_VALUES_FILE"
MAX_LINE_BYTES = 3900  # one os.write below 4 KB is atomic on an O_APPEND descriptor
MAX_MESSAGE_CHARS = 500
MASK = "***"
MIN_SECRET_LEN = 3
DEFAULT_WORKER = "gw0"
CRASH_WHEN = "???"
_PAIR = re.compile(r"(?i)\b((?:password|passwd|token|secret|authorization)\s*[:=]\s*)\S+")
_BEARER = re.compile(r"(?i)\b(Bearer|Basic)(\s+)[A-Za-z0-9._~+/=-]{6,}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class SecretMasker:
    """Replaces known secret values and secret-looking pairs. The console masks again on its side."""

    def __init__(self, values: list[str]) -> None:
        self._values = sorted((v for v in values if len(v) >= MIN_SECRET_LEN), key=len, reverse=True)

    @classmethod
    def from_env(cls) -> SecretMasker:
        path = os.environ.get(ENV_SECRETS_FILE)
        if not path:
            return cls([])
        try:
            with open(path, encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (OSError, ValueError):
            return cls([])
        return cls([str(v) for v in loaded] if isinstance(loaded, list) else [])

    def mask(self, text: str) -> str:
        for value in self._values:
            text = text.replace(value, MASK)
        text = _BEARER.sub(rf"\1\2{MASK}", text)
        return _PAIR.sub(rf"\1{MASK}", text)

    def mask_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {key: self._mask_value(value) for key, value in record.items()}

    def _mask_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.mask(value)
        if isinstance(value, list):
            return [self._mask_value(item) for item in value]
        return value


class EventWriter:
    """Appends whole lines with one os.write each. A failure disables the writer, never the test run."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._fd: int | None = None
        self._broken = False

    def write(self, record: dict[str, Any]) -> None:
        if self._broken:
            return
        try:
            if self._fd is None:
                os.makedirs(os.path.dirname(os.path.abspath(self._path)), exist_ok=True)
                self._fd = os.open(self._path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            os.write(self._fd, _encode(record))
        except OSError as error:
            self._broken = True
            sys.stderr.write(f"console_events: cannot write {self._path}: {error.__class__.__name__}\n")


def _encode(record: dict[str, Any]) -> bytes:
    line = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
    message = record.get("message")
    while len(line) > MAX_LINE_BYTES and isinstance(message, str) and message:
        message = message[: len(message) // 2]
        line = json.dumps({**record, "message": message}, ensure_ascii=True, separators=(",", ":"))
    return (line + "\n").encode("ascii")


def _chunks(nodeids: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = [[]]
    size = 0
    for nodeid in nodeids:
        cost = len(json.dumps(nodeid)) + 1
        if chunks[-1] and size + cost > MAX_LINE_BYTES - 200:
            chunks.append([])
            size = 0
        chunks[-1].append(nodeid)
        size += cost
    return [chunk for chunk in chunks if chunk]


def worker_id(config: pytest.Config) -> str:
    return str(getattr(config, "workerinput", {}).get("workerid", DEFAULT_WORKER))


def _crash_message(report: pytest.TestReport) -> str:
    longrepr = report.longrepr
    reprcrash = getattr(longrepr, "reprcrash", None)
    text = getattr(reprcrash, "message", None) or str(longrepr or "")
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first[:MAX_MESSAGE_CHARS]


def _skip_reason(report: pytest.TestReport) -> str:
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2]).removeprefix("Skipped: ")[:MAX_MESSAGE_CHARS]
    return str(getattr(report, "wasxfail", "") or "")[:MAX_MESSAGE_CHARS]


def combine_outcome(reports: list[pytest.TestReport]) -> str:
    """One outcome for the setup, call and teardown reports of an attempt."""
    if any(str(r.outcome) == "rerun" for r in reports):
        return "rerun"
    if any(r.failed for r in reports):
        return "failed"
    for report in reports:
        if hasattr(report, "wasxfail"):
            return "xfailed" if report.skipped else "xpassed"
    return "skipped" if any(r.skipped for r in reports) else "passed"


class EventsReporter:
    """The hooks. Registered only when CONSOLE_EVENTS_FILE is set."""

    def __init__(self, config: pytest.Config, writer: EventWriter, masker: SecretMasker) -> None:
        self._config = config
        self._writer = writer
        self._masker = masker
        self._reports: dict[str, list[pytest.TestReport]] = {}
        self._reruns: dict[str, int] = {}
        self._collected_written = False

    # ---- who writes what -------------------------------------------------------------------

    def _is_worker(self) -> bool:
        return hasattr(self._config, "workerinput")

    def _is_controller(self) -> bool:
        return not self._is_worker() and self._config.pluginmanager.has_plugin("dsession")

    def _runs_tests_here(self) -> bool:
        return not self._is_controller()

    def _emit(self, record: dict[str, Any]) -> None:
        self._writer.write(self._masker.mask_record({**record, "ts": _now()}))

    def _log(self, level: str, message: str, nodeid: str | None = None) -> None:
        record: dict[str, Any] = {"t": "log", "level": level, "source": "runner", "message": message}
        if nodeid:
            record["nodeid"] = nodeid
        self._emit(record)

    # ---- collection ------------------------------------------------------------------------

    def _write_collected(self, nodeids: list[str]) -> None:
        if self._collected_written:
            return
        self._collected_written = True
        self._emit({"t": "collected", "total": len(nodeids)})
        for chunk in _chunks(nodeids):
            self._emit({"t": "queued", "nodeids": chunk})
        self._log("INFO", f"pytest  {len(nodeids)} tests collected")

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        if self._runs_tests_here() and not self._is_worker():
            self._write_collected([item.nodeid for item in session.items])

    @pytest.hookimpl(optionalhook=True)
    def pytest_xdist_node_collection_finished(self, node: Any, ids: list[str]) -> None:
        self._write_collected(list(ids))

    # ---- tests -----------------------------------------------------------------------------

    def pytest_runtest_logstart(self, nodeid: str, location: Any) -> None:
        if not self._runs_tests_here():
            return
        self._reports[nodeid] = []
        self._emit({"t": "start", "nodeid": nodeid, "worker": worker_id(self._config)})

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == CRASH_WHEN:
            self._write_crash(report)
        elif self._runs_tests_here():
            self._collect_report(report)

    def _collect_report(self, report: pytest.TestReport) -> None:
        attempt = self._reports.setdefault(report.nodeid, [])
        attempt.append(report)
        if report.when == "teardown":
            self._write_end(report.nodeid, attempt)

    def _write_end(self, nodeid: str, reports: list[pytest.TestReport]) -> None:
        outcome = combine_outcome(reports)
        outcome = self._flaky_or_counted(nodeid, outcome)
        record: dict[str, Any] = {
            "t": "end",
            "nodeid": nodeid,
            "worker": worker_id(self._config),
            "outcome": outcome,
            "durationMs": round(sum(r.duration for r in reports) * 1000),
        }
        record.update(self._details(nodeid, outcome, reports))
        self._emit(record)

    def _flaky_or_counted(self, nodeid: str, outcome: str) -> str:
        if outcome == "rerun":
            self._reruns[nodeid] = self._reruns.get(nodeid, 0) + 1
        elif outcome == "passed" and self._reruns.get(nodeid):
            return "flaky"
        return outcome

    def _details(self, nodeid: str, outcome: str, reports: list[pytest.TestReport]) -> dict[str, Any]:
        failed = next((r for r in reports if r.failed or str(r.outcome) == "rerun"), None)
        if failed is not None:
            return self._failure_details(nodeid, outcome, failed)
        skipped = next((r for r in reports if r.skipped), None)
        if skipped is not None:
            return {"skipReason": _skip_reason(skipped)}
        return {}

    def _failure_details(self, nodeid: str, outcome: str, report: pytest.TestReport) -> dict[str, Any]:
        message = _crash_message(report)
        level = "WARN" if outcome == "rerun" else ("FAIL" if report.when == "call" else "ERROR")
        prefix = "rerun  " if outcome == "rerun" else ""
        self._log(level, f"{prefix}{message}", nodeid)
        return {"message": message, "setupError": report.when == "setup"}

    def _write_crash(self, report: pytest.TestReport) -> None:
        node = getattr(report, "node", None)
        worker = str(getattr(node, "workerinput", {}).get("workerid", DEFAULT_WORKER))
        self._log("ERROR", f"worker '{worker}' crashed while running {report.nodeid}", report.nodeid)
        self._emit(
            {
                "t": "end",
                "nodeid": report.nodeid,
                "worker": worker,
                "outcome": "failed",
                "durationMs": 0,
                "message": _crash_message(report),
            }
        )

    # ---- session ---------------------------------------------------------------------------

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        if not self._is_worker():
            self._emit({"t": "session_end", "exitstatus": int(exitstatus)})


def pytest_configure(config: pytest.Config) -> None:
    path = os.environ.get(ENV_EVENTS_FILE)
    if not path:
        return
    reporter = EventsReporter(config, EventWriter(path), SecretMasker.from_env())
    config.pluginmanager.register(reporter, "console-events")
