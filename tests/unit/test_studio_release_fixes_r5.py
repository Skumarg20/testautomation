"""Release QA round 5: the issues the QA agents found in team-mode Test Studio, one test (or more) each.
No browser and no MargBooks."""
from __future__ import annotations

import socket
import time
from pathlib import Path

import pytest

from ui_studio import memory, server, state, verify

from tests.unit.test_studio_release_fixes import srv, _login, _call   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "studio_settings.json")
    monkeypatch.setattr(memory, "ALIASES_FILE", tmp_path / "aliases.json")
    memory._cache["stamp"] = None
    state.save_settings({"out_dir": str(tmp_path / "specs"), "ai_mode": "never"})
    yield
    memory._cache["stamp"] = None


# ================================================================ record: books5 vs the environment under test

def test_record_bat_never_defaults_to_books5():
    raw = (ROOT / "record.bat").read_bytes()
    text = raw.decode("ascii")
    assert b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n")     # CRLF only
    assert "_start.bat" in text
    assert "books5" not in text.lower()
    assert "set /p" in text.lower()                                     # no URL given: it asks for one
    assert "books5" not in (ROOT / "ui_studio" / "DEPLOY.md").read_text(encoding="utf-8").split("## 7.")[1].split("## 8.")[0]
    app = (ROOT / "ui_studio" / "app.html").read_text(encoding="utf-8")
    assert 'id="recBat"' in app                                          # the Record screen shows record.bat <URL>


CODE = """import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('https://books5.margbooks.com/mb/utillity-menu');
  await page.getByRole('button', { name: 'Save' }).click();
  await page.goto("https://books6.margbooks.com/mb/dashboard");
  await page.goto('https://accounts.margbooks.com/login');
});"""


def test_verify_flags_and_fixes_a_goto_on_another_margbooks(monkeypatch):
    monkeypatch.setattr(verify, "_env", lambda: {"app_url": "https://books6.margbooks.com/",
                                                 "login_url": "https://books6.margbooks.com/login"})
    f = next(x for x in verify._findings(CODE) if x.id == "host")
    assert f.sev == "Must fix" and "books5.margbooks.com" in f.why and "books6.margbooks.com" in f.why
    assert f.old == ["  await page.goto('https://books5.margbooks.com/mb/utillity-menu');"]
    fixed = verify.apply(CODE, ["host"])
    assert "books5" not in fixed
    assert "goto('https://books6.margbooks.com/mb/utillity-menu')" in fixed
    assert "https://accounts.margbooks.com/login" in fixed                # the shared sign-in host is left alone
    assert not any(x.id == "host" for x in verify._findings(fixed))
    monkeypatch.setattr(verify, "_env", lambda: {})                     # no environment set up: nothing to compare
    assert not any(x.id == "host" for x in verify._findings(CODE))


# ================================================================ ops: header trickle (slowloris)

def test_a_client_trickling_header_bytes_is_dropped_at_the_header_deadline(srv, monkeypatch):   # noqa: F811
    monkeypatch.setattr(server.Handler, "HEADER_SECONDS", 1.5)
    assert server.Handler.HEADER_SECONDS < server.Handler.timeout
    host, port = srv.replace("http://", "").split(":")
    s = socket.create_connection((host, int(port)), timeout=10)
    s.sendall(b"GET /api/state HTTP/1.1\r\nHost: x\r\nX-A: ")
    t0 = time.time()
    got = b""
    try:
        for _ in range(12):                    # one byte every 0.5 s: each recv is well inside `timeout`
            s.sendall(b"a")
            s.settimeout(0.5)
            try:
                got = s.recv(100)
                break                          # closed (b"") or answered
            except socket.timeout:
                pass
    except OSError:
        got = b""                              # reset by the server: dropped too
    assert time.time() - t0 < 5.5
    assert got == b""                          # dropped without an answer
    s.close()
    # a normal request on a new connection still works
    assert _call(_login(srv, "qa1@qa.test"), srv, "/api/state")[0] == 200


def test_keep_alive_connection_waiting_for_its_next_request_is_not_cut_by_the_header_deadline(srv, monkeypatch):   # noqa: F811
    import http.client
    monkeypatch.setattr(server.Handler, "HEADER_SECONDS", 1)
    host, port = srv.replace("http://", "").split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=10)
    c.request("GET", "/healthz")
    assert c.getresponse().read() and True
    time.sleep(2)                              # idle longer than HEADER_SECONDS (but not `timeout`)
    c.request("GET", "/healthz")
    r = c.getresponse()
    assert r.status == 200
    c.close()


# ================================================================ ops: wrong JSON types -> 400, never Python text

@pytest.mark.parametrize("path,body", [
    ("/api/me/margbooks", {"user": 1, "password": {"x": 1}}),
    ("/api/verify", {"code": ["x"]}),
    ("/api/verify/apply", {"code": 1, "ids": "x"}),
    ("/api/write/generate", {"name": 1, "module": [], "lines": 3}),
    ("/api/record/paste", {"code": {"a": 1}}),
    ("/api/write/check", {"lines": [1, 2]}),
    ("/api/run", {"ids": [1]}),
])
def test_wrong_type_fields_get_a_plain_400(srv, path, body):   # noqa: F811
    code, d, _ = _call(_login(srv, "qa1@qa.test"), srv, path, body)
    assert code == 400, d
    assert "must be" in d["error"] and "Error" not in d["error"] and "object has no attribute" not in d["error"]


@pytest.mark.parametrize("path,body", [
    ("/api/scripts/save", {"node": 1, "text": 2}),
    ("/api/scripts/new", {"case": ["x"]}),
])
def test_wrong_type_fields_on_admin_endpoints_get_a_plain_400(srv, path, body):   # noqa: F811
    code, d, _ = _call(_login(srv, "boss@qa.test"), srv, path, body)
    assert code == 400 and "must be text" in d["error"], d


def test_an_unexpected_error_never_sends_exception_text_to_the_browser(srv, monkeypatch, capsys):   # noqa: F811
    def boom(b):
        raise OSError(r"[Errno 13] Permission denied: 'C:\\secret\\server\\path\\studio.db'")
    monkeypatch.setitem(server.POST, "/api/verify", boom)
    code, d, _ = _call(_login(srv, "qa1@qa.test"), srv, "/api/verify", {"code": "x"})
    assert code == 500
    assert "secret" not in d["error"] and "Permission" not in d["error"] and "OSError" not in d["error"]
    assert "server log" in d["error"]
    assert "Permission denied" in capsys.readouterr().err                 # the details are in the server log


def test_body_type_check_allows_what_the_studio_page_sends():
    b = {"code": "x", "name": "n", "module": "Sale", "lines": ["a"], "ids": ["TC_1"], "password": None,
         "video": True, "bulk": {"party": True}, "token_limit": 5, "headed": False}
    assert server.check_body_types(b) is b
    with pytest.raises(server.Bad, match="must be a list of text"):
        server.check_body_types({"lines": "x"})
