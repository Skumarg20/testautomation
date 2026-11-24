"""Logged-in sessions: one-shot sessionStorage restore, credentials in CI, cleanup and capture hooks."""

import json
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, Route

from config.settings import settings
from fixtures import console_capture, session, steps
from fixtures.recording import OVERLAY_SCRIPT
from fixtures.session import AccountSessions, MissingCredentialsError

pytestmark = pytest.mark.framework

ORIGIN = "http://session-restore.test"
APP = "<html><body>app</body></html>"


def _serve(route: Route) -> None:
    route.fulfill(status=200, content_type="text/html", body=APP)


def test_saved_session_storage_is_restored_once_and_app_changes_survive_a_reload(page: Page) -> None:
    page.route(f"{ORIGIN}/**", _serve)
    page.add_init_script(session.restore_script_for(ORIGIN, {"token": "login-time"}))
    page.goto(f"{ORIGIN}/")
    assert page.evaluate("sessionStorage.getItem('token')") == "login-time"

    page.evaluate("sessionStorage.setItem('token', 'refreshed')")
    page.reload()
    assert page.evaluate("sessionStorage.getItem('token')") == "refreshed"

    page.evaluate("sessionStorage.removeItem('token')")  # the app logs out
    page.goto(f"{ORIGIN}/other")
    assert page.evaluate("sessionStorage.getItem('token')") is None


def test_logout_that_clears_all_session_storage_is_not_undone_by_a_reload(page: Page) -> None:
    page.route(f"{ORIGIN}/**", _serve)
    page.add_init_script(session.restore_script_for(ORIGIN, {"token": "login-time"}))
    page.goto(f"{ORIGIN}/")
    assert page.evaluate("sessionStorage.getItem('token')") == "login-time"

    page.evaluate("sessionStorage.clear()")  # the usual SPA logout
    page.reload()
    assert page.evaluate("sessionStorage.getItem('token')") is None
    page.goto(f"{ORIGIN}/other")
    assert page.evaluate("sessionStorage.getItem('token')") is None


def test_a_new_tab_gets_the_saved_session_storage(page: Page) -> None:
    script = session.restore_script_for(ORIGIN, {"token": "login-time"})
    page.context.add_init_script(script)
    page.context.route(f"{ORIGIN}/**", _serve)
    page.goto(f"{ORIGIN}/")
    page.evaluate("sessionStorage.clear()")
    other = page.context.new_page()
    other.goto(f"{ORIGIN}/")
    assert other.evaluate("sessionStorage.getItem('token')") == "login-time"


def test_missing_credentials_skip_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qa_require_credentials", False)
    with pytest.raises(pytest.skip.Exception):
        session.report_missing_credentials(MissingCredentialsError("chemist"))


def test_missing_credentials_fail_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qa_require_credentials", True)
    with pytest.raises(pytest.fail.Exception, match="chemist"):
        session.report_missing_credentials(MissingCredentialsError("chemist"))


class _FakeContext:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    def add_init_script(self, script: str) -> None:
        self.scripts.append(script)

    def storage_state(self, path: str) -> None:
        Path(path).write_text(json.dumps({"cookies": [], "origins": []}))


class _FakePage:
    def evaluate(self, _: str) -> dict[str, str]:
        return {"token": "t"}


def test_saved_session_files_are_removed_at_the_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(session, "AUTH_DIRECTORY", tmp_path)
    sessions = AccountSessions(browser=Any, context_options={}, worker_id="gw0")  # type: ignore[arg-type]
    sessions._save_session("chemist", _FakeContext(), _FakePage())  # type: ignore[arg-type]
    assert len(list(tmp_path.iterdir())) == 2

    sessions.remove_saved_sessions()

    assert list(tmp_path.iterdir()) == []


def test_every_context_gets_the_overlay_steps_and_console_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    attached: list[str] = []
    monkeypatch.setattr(steps, "enabled", lambda: True)
    monkeypatch.setattr(steps, "attach_context", lambda _: attached.append("steps"))
    monkeypatch.setattr(console_capture, "enabled", lambda: True)
    monkeypatch.setattr(console_capture, "attach_context", lambda _: attached.append("console"))
    context = _FakeContext()

    session.instrument_context(context, Path("rec"))  # type: ignore[arg-type]

    assert context.scripts == [OVERLAY_SCRIPT]
    assert attached == ["steps", "console"]
