"""QA Console capture plugin: Given/When/Then steps, network calls, axe findings, trace and screenshots.

Everything here is inert unless the environment variable CONSOLE_STEPS is "1" (the console sets it per run).
Results travel through the pytest-json-report `metadata` object of each test (hook is optional, so a run with
`-p no:jsonreport` still works). The console ingester turns the metadata into rows (F04 section 5.6).

Environment, all read at test time:
  CONSOLE_STEPS=1                  master switch
  CONSOLE_CAPTURE_NETWORK=1        record network calls for every test (tests marked `api` always record)
  CONSOLE_CAPTURE_TRACE            off | retain-on-failure (default) | on
  CONSOLE_CAPTURE_SCREENSHOT       off | only-on-failure (default) | on
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import linecache
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import FrameType, TracebackType
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page, Request, Response

log = logging.getLogger("console.steps")

ENV_ENABLED = "CONSOLE_STEPS"
ENV_NETWORK = "CONSOLE_CAPTURE_NETWORK"
ENV_TRACE = "CONSOLE_CAPTURE_TRACE"
ENV_SCREENSHOT = "CONSOLE_CAPTURE_SCREENSHOT"
MAX_STEPS = 200
MAX_NETWORK = 500
MAX_A11Y = 100
MAX_CODE_CHARS = 200
MASK = "***"
RECORDED_RESOURCES = frozenset({"xhr", "fetch", "document"})
BLOCKING_IMPACTS = ("serious", "critical")
KNOWN_IMPACTS = ("critical", "serious", "moderate", "minor")
ELEMENT_TIMEOUT_MS = 1000
SCREENSHOT_TIMEOUT_MS = 5000
_SENSITIVE_NAME = re.compile(r"(?i)password|otp|token")
_SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)(\b[\w.]*(?:password|otp|token)\w*["']?\s*[=:]\s*)("[^"]*"|'[^']*'|[^\s,)\]}]+)"""
)


def enabled() -> bool:
    return os.environ.get(ENV_ENABLED) == "1"


def mask_secrets(text: str) -> str:
    """Values assigned to names containing password, otp or token become `***`."""
    return _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}{MASK}", text)


# ---- per-test state -------------------------------------------------------------------------------


@dataclass
class _CaptureState:
    slug: str
    output_dir: Path
    network_on: bool
    steps: list[dict[str, Any]] = field(default_factory=list)
    plan: list[tuple[str, str]] = field(default_factory=list)
    network: list[dict[str, Any]] = field(default_factory=list)
    a11y: list[dict[str, Any]] = field(default_factory=list)
    contexts: list[BrowserContext] = field(default_factory=list)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    element_state: dict[str, Any] | None = None
    setup_error: bool = False
    truncated: bool = False
    closed: bool = False
    request_started: dict[int, float] = field(default_factory=dict)

    def as_metadata(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "steps": self._steps_with_not_run(),
            "network": self.network,
            "a11y": self.a11y,
            "artifact_slug": self.slug,
            "artifacts": self.artifacts,
        }
        if self.element_state:
            data["element_state"] = self.element_state
        if self.setup_error:
            data["setup_error"] = True
        if self.truncated:
            data["truncated"] = True
        return data

    def _steps_with_not_run(self) -> list[dict[str, Any]]:
        if not any(entry["outcome"] == "failed" for entry in self.steps):
            return list(self.steps)
        entered = {(entry["keyword"], entry["text"]) for entry in self.steps}
        missing = [item for item in self.plan if item not in entered]
        not_run = [_step_entry(len(self.steps) + n, kw, text) for n, (kw, text) in enumerate(missing, 1)]
        return [*self.steps, *not_run]


_KEY: pytest.StashKey[_CaptureState] = pytest.StashKey()
_current: _CaptureState | None = None


def _step_entry(seq: int, keyword: str, text: str) -> dict[str, Any]:
    return {
        "seq": seq,
        "keyword": keyword,
        "text": mask_secrets(text),
        "code": None,
        "duration_ms": 0,
        "outcome": "not_run",
    }


# ---- steps ----------------------------------------------------------------------------------------


@lru_cache(maxsize=64)
def _parsed(path: str) -> ast.Module | None:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None


def _first_body_line(path: str, line: int) -> int | None:
    """Line of the first statement inside the innermost `with` whose header covers `line`."""
    tree = _parsed(path)
    if tree is None:
        return None
    best: ast.With | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.With) and node.lineno <= line <= _header_end(node):
            best = node if best is None or node.lineno >= best.lineno else best
    return best.body[0].lineno if best else None


def _header_end(node: ast.With) -> int:
    return max(item.context_expr.end_lineno or node.lineno for item in node.items)


def _source_line(path: str, line: int) -> str:
    return linecache.getline(path, line).strip()[:MAX_CODE_CHARS]


def _failing_line(path: str, tb: TracebackType | None) -> int | None:
    """Deepest traceback line that lies in `path`."""
    found: int | None = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == path:
            found = tb.tb_lineno
        tb = tb.tb_next
    return found


def _caller_frame() -> FrameType | None:
    frame: FrameType | None = sys._getframe(1)
    while frame is not None and frame.f_code.co_filename == __file__:
        frame = frame.f_back
    return frame


def _describe_args(args: dict[str, Any]) -> str:
    shown = {name: MASK if _SENSITIVE_NAME.search(name) else repr(value) for name, value in args.items()}
    return ", ".join(f"{name}={value}" for name, value in shown.items())


class _Step:
    """Context manager that records one step. Exceptions are re-raised unchanged."""

    def __init__(self, keyword: str, text: str, args: dict[str, Any]) -> None:
        self._keyword = keyword
        self._text = text
        self._args = args
        self._entry: dict[str, Any] | None = None
        self._path = ""
        self._started = 0.0

    def __enter__(self) -> _Step:
        state = _current
        if state is None:
            return self
        if len(state.steps) >= MAX_STEPS:
            state.truncated = True
            return self
        frame = _caller_frame()
        self._started = time.perf_counter()
        self._entry = _step_entry(len(state.steps) + 1, self._keyword, self._text)
        self._entry["outcome"] = "passed"
        if frame is not None:
            self._path = frame.f_code.co_filename
            self._entry["code"] = self._code_at(frame.f_lineno)
        state.steps.append(self._entry)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: TracebackType | None) -> None:
        entry = self._entry
        if entry is None:
            return
        entry["duration_ms"] = round((time.perf_counter() - self._started) * 1000)
        if exc_type is None:
            return
        entry["outcome"] = "not_run" if issubclass(exc_type, pytest.skip.Exception) else "failed"
        line = _failing_line(self._path, tb)
        if line is not None and entry["outcome"] == "failed":
            entry["code"] = self._with_args(_source_line(self._path, line))

    def _code_at(self, header_line: int) -> str:
        body_line = _first_body_line(self._path, header_line) or header_line
        return self._with_args(_source_line(self._path, body_line))

    def _with_args(self, line: str) -> str:
        code = mask_secrets(line)
        return f"{code}  # {_describe_args(self._args)}" if self._args else code


class _StepFactory:
    def __call__(self, keyword: str, text: str, **args: Any) -> _Step:
        return _Step(keyword, text, args)

    def plan(self, steps: list[tuple[str, str]]) -> None:
        """Declare the steps up front; those never entered after a failure are stored as `not_run`."""
        if _current is not None:
            _current.plan = [(keyword, text) for keyword, text in steps]


step = _StepFactory()


def given(text: str, **args: Any) -> _Step:
    return step("Given", text, **args)


def when(text: str, **args: Any) -> _Step:
    return step("When", text, **args)


def then(text: str, **args: Any) -> _Step:
    return step("Then", text, **args)


def and_(text: str, **args: Any) -> _Step:
    return step("And", text, **args)


# ---- network --------------------------------------------------------------------------------------


def _path_only(url: str) -> str:
    return urlsplit(url).path or "/"


def _append_network(state: _CaptureState, row: dict[str, Any]) -> None:
    if len(state.network) >= MAX_NETWORK:
        state.truncated = True
        return
    state.network.append(row)


def _watch_network(state: _CaptureState, context: BrowserContext) -> None:
    def on_request(request: Request) -> None:
        state.request_started[id(request)] = time.perf_counter()

    def on_response(response: Response) -> None:
        request = response.request
        if request.resource_type not in RECORDED_RESOURCES:
            return
        started = state.request_started.pop(id(request), None)
        elapsed = None if started is None else round((time.perf_counter() - started) * 1000)
        row = {"method": request.method, "path": _path_only(request.url), "status": response.status}
        _append_network(state, {**row, "duration_ms": elapsed})

    def on_failed(request: Request) -> None:
        if request.resource_type in RECORDED_RESOURCES:
            state.request_started.pop(id(request), None)
            row = {"method": request.method, "path": _path_only(request.url), "status": None}
            _append_network(state, {**row, "duration_ms": None})

    context.on("request", on_request)
    context.on("response", on_response)
    context.on("requestfailed", on_failed)


# ---- accessibility --------------------------------------------------------------------------------


def _flatten_target(target: Any) -> str:
    if isinstance(target, (list, tuple)):
        return " >> ".join(_flatten_target(part) for part in target)
    return str(target)


def finding_from_violation(violation: dict[str, Any]) -> dict[str, Any]:
    """One finding per axe violation (F04 5.6 item 6). A missing impact is stored as `minor`."""
    nodes = violation.get("nodes") or []
    impact = violation.get("impact")
    return {
        "rule": str(violation.get("id", "")),
        "impact": impact if impact in KNOWN_IMPACTS else "minor",
        "target": _flatten_target(nodes[0].get("target", "")) if nodes else "",
        "detail": str(violation.get("help", "")),
        "node_count": len(nodes),
    }


def check_a11y(page: Page) -> list[dict[str, Any]]:
    """Run axe on the page and store the findings (plugin on). Serious or critical findings fail the test."""
    from axe_playwright_python.sync_playwright import Axe

    violations = Axe().run(page).response["violations"]
    findings = [finding_from_violation(violation) for violation in violations]
    _store_findings(findings)
    blocking = [item for item in findings if item["impact"] in BLOCKING_IMPACTS]
    if blocking:
        listed = ", ".join(f"{item['rule']} ({item['impact']})" for item in blocking)
        raise AssertionError(f"Accessibility violations: {listed}")
    return findings


def _store_findings(findings: list[dict[str, Any]]) -> None:
    state = _current
    if state is None:
        return
    room = MAX_A11Y - len(state.a11y)
    state.truncated = state.truncated or len(findings) > room
    state.a11y.extend(findings[: max(room, 0)])


# ---- context hook for AccountSessions -------------------------------------------------------------


def _trace_mode() -> str:
    return os.environ.get(ENV_TRACE, "retain-on-failure")


def _screenshot_mode() -> str:
    return os.environ.get(ENV_SCREENSHOT, "only-on-failure")


def attach_context(context: BrowserContext) -> None:
    """Called by AccountSessions for each context a test opens: tracing and network capture start here."""
    state = _current
    if state is None:
        return
    state.contexts.append(context)
    if _trace_mode() != "off":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    if state.network_on:
        _watch_network(state, context)


# ---- finishing a test: element state, screenshots, traces ----------------------------------------


def _is_failure(call: pytest.CallInfo[Any]) -> bool:
    excinfo = call.excinfo
    if excinfo is None:
        return False
    return not excinfo.errisinstance((pytest.skip.Exception, pytest.xfail.Exception))


# Playwright has no public API for "which locator did this expect() fail on". The two functions below are
# the only place that touches its private names (`_actual_locator`, `_generated.mapping`, `_impl_obj`,
# `_selector`); tests/framework/test_playwright_internals.py fails when an upgrade changes them.


def _locator_from(tb: TracebackType | None) -> Any:
    """The locator of the last failed `expect(...)` assertion on the traceback, as a sync Locator."""
    found: Any = None
    while tb is not None:
        owner = tb.tb_frame.f_locals.get("self")
        found = getattr(owner, "_actual_locator", found)
        tb = tb.tb_next
    if found is None:
        return None
    mapping = importlib.import_module("playwright.sync_api._generated").mapping
    return mapping.from_impl(found)


def _selector_of(locator: Any) -> str:
    return str(getattr(locator, "_impl_obj", locator)._selector)


def _read_element_state(excinfo: pytest.ExceptionInfo[BaseException]) -> dict[str, Any] | None:
    locator = _locator_from(excinfo.tb)
    if locator is None:
        return None
    return {
        "locator": mask_secrets(_selector_of(locator))[:200],
        "text": locator.inner_text(timeout=ELEMENT_TIMEOUT_MS)[:200],
        "visible": locator.is_visible(),
    }


def _best_effort(action: str, work: Any) -> Any:
    try:
        return work()
    except Exception as error:  # noqa: BLE001 - capture must never fail or hide the test result
        log.debug("capture step %s failed: %s", action, type(error).__name__)
        return None


def _try_screenshot(page: Page, path: Path) -> bool:
    try:
        page.screenshot(path=path, timeout=SCREENSHOT_TIMEOUT_MS)
    except Exception as error:  # noqa: BLE001 - a closed page must not hide the test result
        log.debug("screenshot failed: %s", type(error).__name__)
        return False
    return True


def _save_screenshots(state: _CaptureState) -> None:
    pages: list[Page] = [page for context in state.contexts for page in context.pages]
    state.output_dir.mkdir(parents=True, exist_ok=True)
    for index, page in enumerate(pages, 1):
        path = state.output_dir / f"test-failed-{index}.png"
        if _try_screenshot(page, path):
            state.artifacts.append({"kind": "screenshot", "file": path.name})


def _try_stop_trace(context: BrowserContext, path: Path | None) -> bool:
    try:
        context.tracing.stop(path=path)
    except Exception as error:  # noqa: BLE001 - a closed context must not hide the test result
        log.debug("trace stop failed: %s", type(error).__name__)
        return False
    return path is not None


def _stop_traces(state: _CaptureState, keep: bool) -> None:
    if _trace_mode() == "off":
        return
    state.output_dir.mkdir(parents=True, exist_ok=True)
    for index, context in enumerate(state.contexts, 1):
        name = "trace.zip" if len(state.contexts) == 1 else f"trace-{index}.zip"
        if _try_stop_trace(context, state.output_dir / name if keep else None):
            state.artifacts.append({"kind": "trace", "file": name})


def _finish(state: _CaptureState, call: pytest.CallInfo[Any]) -> None:
    failed = _is_failure(call)
    if failed and call.excinfo is not None:
        state.element_state = _best_effort("element", lambda: _read_element_state(call.excinfo))
    if failed and call.when == "setup":
        state.setup_error = True
    if failed and _screenshot_mode() != "off" or _screenshot_mode() == "on":
        _save_screenshots(state)
    _stop_traces(state, keep=failed or _trace_mode() == "on")
    state.closed = True


# ---- pytest hooks (registered when this module is a plugin) --------------------------------------


def slug_of(nodeid: str) -> str:
    from slugify import slugify

    name = slugify(nodeid)
    if len(name) < 256:
        return name
    return f"{name[:100]}-{hashlib.sha256(name.encode()).hexdigest()[:7]}-{name[-100:]}"


def _output_dir(item: pytest.Item) -> Path:
    option = item.config.getoption("--output", default=None) or "test-results"
    return Path(option).absolute() / slug_of(item.nodeid)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    global _current  # noqa: PLW0603 - one test runs at a time per process; steps() has no item to read
    if not enabled():
        return
    network_on = os.environ.get(ENV_NETWORK) == "1" or item.get_closest_marker("api") is not None
    _current = _CaptureState(slug_of(item.nodeid), _output_dir(item), network_on)
    item.stash[_KEY] = _current


def _ends_capture(call: pytest.CallInfo[Any]) -> bool:
    return call.when == "call" or (call.when == "setup" and call.excinfo is not None)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> Any:
    state = item.stash.get(_KEY, None)
    if state is not None and not state.closed and _ends_capture(call):
        _finish(state, call)
    yield


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    global _current  # noqa: PLW0603
    if _current is not None and item.stash.get(_KEY, None) is _current:
        _current = None


@pytest.hookimpl(optionalhook=True)
def pytest_json_runtest_metadata(item: pytest.Item, call: pytest.CallInfo[Any]) -> dict[str, Any]:
    state = item.stash.get(_KEY, None)
    if state is None or call.when == "teardown" or not state.closed:
        return {}
    return state.as_metadata()
