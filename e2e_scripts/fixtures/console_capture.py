"""Browser console and network capture for the QA Console (F03 Console and Network log tabs).

Inert unless the environment variable CONSOLE_CAPTURE_LOGS is "1" (the console sets it per run): no
listener is attached and nothing is written. When on, every browser context a test opens through
`AccountSessions` is watched, and at the end of the test two JSON-lines files are written:

  <root>/<runId>/<test slug>/console.jsonl   {"time","type","level","text","url"}
  <root>/<runId>/<test slug>/network.jsonl   {"time","method","url","status","duration","resourceType",
                                              "failure"?}

`root` is env CONSOLE_CAPTURE_DIR, default `results/capture`; `runId` is env CONSOLE_RUN_ID (default
`local`); the slug is the one `fixtures.steps` uses for artifacts. `time` is UTC ISO-8601 with milliseconds,
`duration` is milliseconds (null when unknown), `status` is null when the request failed. A file is written
only when the test produced at least one line of that kind.

Secrets (rule 5): request and response headers, cookies and bodies are never read. Text and URLs are masked:
`password=`, `token=`, `authorization:` pairs, Bearer/Basic values, URL userinfo (`//user:pw@`), cookie pairs,
secret-looking query values, and the values listed in CONSOLE_SECRET_VALUES_FILE.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from fixtures.steps import slug_of
from plugins.console_events import SecretMasker

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, ConsoleMessage, Request, Response, WebError

ENV_ENABLED = "CONSOLE_CAPTURE_LOGS"
ENV_ROOT = "CONSOLE_CAPTURE_DIR"
ENV_RUN_ID = "CONSOLE_RUN_ID"
DEFAULT_RUN_ID = "local"
E2E_DIR = Path(__file__).resolve().parents[1]
MAX_LINES_PER_FILE = 2000
MAX_TEXT_CHARS = 2000
RECORDED_RESOURCES = frozenset({"xhr", "fetch", "document"})
LEVEL_OF_TYPE = {"error": "ERROR", "pageerror": "ERROR", "warning": "WARN"}
_SECRET_QUERY = re.compile(r"(?i)([?&][^=&#\s]*(?:token|key|secret|pass)[^=&#\s]*=)[^&#\s]*")
_URL_USERINFO = re.compile(r"//[^/@\s]+@")
_COOKIE_PAIR = re.compile(r"(?i)\b((?:set-)?cookie\s*[:=]\s*)[^\r\n]+")


def enabled() -> bool:
    return os.environ.get(ENV_ENABLED) == "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass
class CaptureBuffer:
    """Lines of one test, masked as they arrive, written once at the end."""

    masker: SecretMasker
    console: list[dict[str, Any]] = field(default_factory=list)
    network: list[dict[str, Any]] = field(default_factory=list)
    started: dict[int, float] = field(default_factory=dict)

    def mask(self, text: str) -> str:
        text = _URL_USERINFO.sub("//***@", text)
        text = _SECRET_QUERY.sub(r"\1***", text)
        text = _COOKIE_PAIR.sub(r"\1***", text)
        return self.masker.mask(text)

    def add_console(self, kind: str, text: str, url: str) -> None:
        line = {"time": _now(), "type": kind, "level": LEVEL_OF_TYPE.get(kind, "INFO")}
        line["text"] = self.mask(text)[:MAX_TEXT_CHARS]
        line["url"] = self.mask(url)
        _append_capped(self.console, line)

    def request_started(self, request: Request) -> None:
        self.started[id(request)] = time.perf_counter()

    def add_network(self, request: Request, status: int | None, failure: str | None = None) -> None:
        began = self.started.pop(id(request), None)
        duration = None if began is None else round((time.perf_counter() - began) * 1000)
        line: dict[str, Any] = {"time": _now(), "method": request.method, "url": self.mask(request.url)}
        line.update({"status": status, "duration": duration, "resourceType": request.resource_type})
        if failure:
            line["failure"] = self.mask(failure)[:MAX_TEXT_CHARS]
        _append_capped(self.network, line)

    def write_to(self, directory: Path) -> None:
        _write_lines(directory / "console.jsonl", self.console)
        _write_lines(directory / "network.jsonl", self.network)


def _append_capped(lines: list[dict[str, Any]], line: dict[str, Any]) -> None:
    if len(lines) < MAX_LINES_PER_FILE:
        lines.append(line)


def _write_lines(path: Path, lines: list[dict[str, Any]]) -> None:
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(line, ensure_ascii=True, separators=(",", ":")) + "\n" for line in lines)
    path.write_text(body, encoding="utf-8")


def capture_directory(nodeid: str) -> Path:
    root = Path(os.environ.get(ENV_ROOT) or E2E_DIR / "results" / "capture")
    return root / os.environ.get(ENV_RUN_ID, DEFAULT_RUN_ID) / slug_of(nodeid)


# ---- listeners ------------------------------------------------------------------------------------


def watch_context(buffer: CaptureBuffer, context: BrowserContext) -> None:
    def on_console(message: ConsoleMessage) -> None:
        buffer.add_console(message.type, message.text, message.location.get("url", ""))

    def on_web_error(web_error: WebError) -> None:
        buffer.add_console("pageerror", str(web_error.error), "")

    def on_response(response: Response) -> None:
        if response.request.resource_type in RECORDED_RESOURCES:
            buffer.add_network(response.request, response.status)

    def on_failed(request: Request) -> None:
        if request.resource_type in RECORDED_RESOURCES:
            buffer.add_network(request, None, request.failure)

    context.on("console", on_console)
    context.on("weberror", on_web_error)
    context.on("request", buffer.request_started)
    context.on("response", on_response)
    context.on("requestfailed", on_failed)


# ---- hooks and the AccountSessions entry point ---------------------------------------------------

_current: CaptureBuffer | None = None


def attach_context(context: BrowserContext) -> None:
    """Called by AccountSessions for each context a test opens."""
    if _current is not None:
        watch_context(_current, context)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    global _current  # noqa: PLW0603 - one test runs at a time per process; attach_context has no item
    if enabled():
        _current = CaptureBuffer(SecretMasker.from_env())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item: pytest.Item) -> Any:
    yield
    global _current  # noqa: PLW0603
    if _current is not None:
        _current.write_to(capture_directory(item.nodeid))
        _current = None
