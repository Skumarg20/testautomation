"""F03 Network and Console tabs: the capture fixture, driven by fake Playwright objects (no app needed)."""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from fixtures import console_capture
from fixtures.console_capture import CaptureBuffer, watch_context
from plugins.console_events import SecretMasker

pytestmark = pytest.mark.framework

E2E_DIR = Path(__file__).resolve().parents[2]
ANY_TIME = 120
PASSWORD = "S3cret!pw"


class FakeContext:
    def __init__(self) -> None:
        self.handlers: dict[str, Any] = {}

    def on(self, event: str, handler: Any) -> None:
        self.handlers[event] = handler


def fake_request(
    url: str = "https://qa.test/api/items", resource_type: str = "xhr", method: str = "GET"
) -> Any:
    return SimpleNamespace(url=url, resource_type=resource_type, method=method, failure=None)


def watched() -> tuple[FakeContext, CaptureBuffer]:
    buffer = CaptureBuffer(SecretMasker([PASSWORD]))
    context = FakeContext()
    watch_context(buffer, context)  # type: ignore[arg-type]
    return context, buffer


def test_response_becomes_network_line_with_method_url_status_and_duration() -> None:
    context, buffer = watched()
    request = fake_request(method="POST")

    context.handlers["request"](request)
    context.handlers["response"](SimpleNamespace(request=request, status=201))

    line = buffer.network[0]
    assert (line["method"], line["url"], line["status"]) == ("POST", "https://qa.test/api/items", 201)
    assert isinstance(line["duration"], int)
    assert line["time"].endswith("Z")


def test_failed_request_has_null_status_and_failure_text() -> None:
    context, buffer = watched()
    request = fake_request()
    request.failure = "net::ERR_CONNECTION_REFUSED"

    context.handlers["requestfailed"](request)

    assert buffer.network[0]["status"] is None
    assert buffer.network[0]["failure"] == "net::ERR_CONNECTION_REFUSED"


def test_images_and_scripts_are_not_recorded() -> None:
    context, buffer = watched()
    request = fake_request(resource_type="image")

    context.handlers["response"](SimpleNamespace(request=request, status=200))

    assert buffer.network == []


@pytest.mark.parametrize(
    ("kind", "level"), [("log", "INFO"), ("warning", "WARN"), ("error", "ERROR"), ("debug", "INFO")]
)
def test_console_message_type_maps_to_level(kind: str, level: str) -> None:
    context, buffer = watched()
    message = SimpleNamespace(type=kind, text="hello", location={"url": "https://qa.test/app.js"})

    context.handlers["console"](message)

    assert buffer.console[0]["level"] == level
    assert buffer.console[0]["type"] == kind
    assert buffer.console[0]["url"] == "https://qa.test/app.js"


def test_uncaught_page_error_is_an_error_line() -> None:
    context, buffer = watched()

    context.handlers["weberror"](SimpleNamespace(error="TypeError: x is undefined"))

    assert (buffer.console[0]["type"], buffer.console[0]["level"]) == ("pageerror", "ERROR")


def test_secrets_are_masked_in_console_text_and_urls() -> None:
    context, buffer = watched()
    texts = [f"login with {PASSWORD}", "token: abc123xyz", "Bearer abcdefghijkl", "cookie: sid=999; a=b"]
    for text in texts:
        context.handlers["console"](SimpleNamespace(type="log", text=text, location={}))
    request = fake_request(url="https://qa.test/api?access_token=ABC&page=2&apikey=K")
    context.handlers["response"](SimpleNamespace(request=request, status=200))

    written = json.dumps(buffer.console) + json.dumps(buffer.network)

    for leaked in (PASSWORD, "abc123xyz", "abcdefghijkl", "sid=999", "=ABC", "=K"):
        assert leaked not in written
    assert "page=2" in written


def test_url_userinfo_is_masked_in_console_text_and_urls() -> None:
    context, buffer = watched()
    context.handlers["console"](SimpleNamespace(type="log", text="go https://bob:pw9@qa.test/x", location={}))
    request = fake_request(url="https://bob:pw9@qa.test/api")
    context.handlers["response"](SimpleNamespace(request=request, status=200))

    written = json.dumps(buffer.console) + json.dumps(buffer.network)

    assert "pw9" not in written
    assert "bob" not in written
    assert "https://***@qa.test/api" in written


def test_lines_per_file_are_capped() -> None:
    _, buffer = watched()

    for _ in range(console_capture.MAX_LINES_PER_FILE + 5):
        buffer.add_console("log", "x", "")

    assert len(buffer.console) == console_capture.MAX_LINES_PER_FILE


def test_write_creates_one_json_lines_file_per_kind_and_skips_empty_kinds(tmp_path: Path) -> None:
    _, buffer = watched()
    buffer.add_console("log", "hi", "")

    buffer.write_to(tmp_path / "slug")

    assert [json.loads(x)["text"] for x in (tmp_path / "slug/console.jsonl").read_text().splitlines()] == [
        "hi"
    ]
    assert not (tmp_path / "slug/network.jsonl").exists()


SUITE = """
    from fixtures import console_capture

    class Ctx:
        def on(self, event, handler):
            self.handler = getattr(self, "handler", {})
            self.handler[event] = handler

    def test_logs():
        ctx = Ctx()
        console_capture.attach_context(ctx)
        if hasattr(ctx, "handler"):
            ctx.handler["console"](type("M", (), {"type": "log", "text": "hi", "location": {}})())
"""


def run_suite(tmp_path: Path, switch: str | None) -> subprocess.CompletedProcess[str]:
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "pytest.ini").write_text("[pytest]\naddopts = -p no:cacheprovider\n")
    (suite / "test_sample.py").write_text(textwrap.dedent(SUITE))
    for package in ("fixtures", "plugins"):
        shutil.copytree(E2E_DIR / package, suite / package, ignore=shutil.ignore_patterns("__pycache__"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("CONSOLE_")}
    env.update({"CONSOLE_CAPTURE_DIR": str(tmp_path / "out"), "CONSOLE_RUN_ID": "r1"})
    if switch:
        env["CONSOLE_CAPTURE_LOGS"] = switch
    args = [sys.executable, "-m", "pytest", "-p", "fixtures.console_capture", "-q"]
    return subprocess.run(
        args, cwd=suite, env=env, capture_output=True, text=True, timeout=ANY_TIME, check=False
    )


def test_plugin_is_inert_without_the_switch(tmp_path: Path) -> None:
    done = run_suite(tmp_path, switch=None)

    assert done.returncode == 0, done.stdout
    assert not (tmp_path / "out").exists()


def test_plugin_writes_per_test_file_under_run_directory_when_switched_on(tmp_path: Path) -> None:
    done = run_suite(tmp_path, switch="1")

    assert done.returncode == 0, done.stdout
    files = list((tmp_path / "out" / "r1").glob("*/console.jsonl"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["text"] == "hi"
