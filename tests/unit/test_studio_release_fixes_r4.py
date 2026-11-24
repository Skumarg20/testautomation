"""Release QA round 4: the issues the QA agents found in team-mode Test Studio, one test (or more) each.
No browser and no MargBooks: the login, the browser page and the run process are stubs."""
from __future__ import annotations

import gzip
import io
import json
import socket
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from ui_studio import accounts, executor, memory, recorder, script, server, state, tests as studio_tests, verify

from tests.unit.test_studio_release_fixes import srv, store_tmp, _login, LINES   # noqa: F401  (fixtures)
from tests.unit.test_studio_release_fixes_r2 import SAMPLE, _fn, _run_row

APP = (Path(__file__).resolve().parents[2] / "ui_studio" / "app.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "studio_settings.json")
    monkeypatch.setattr(memory, "ALIASES_FILE", tmp_path / "aliases.json")
    memory._cache["stamp"] = None
    state.save_settings({"out_dir": str(tmp_path / "specs")})
    yield
    memory._cache["stamp"] = None


# ================================================================ runs: a sign-in that hangs

def test_login_waits_are_cut_to_the_time_limit_and_stop_ends_them():
    from framework import auth
    assert auth._budget_ms(60000) == 60000                         # outside a sign-in: no limit
    with auth.time_limit(2):
        assert auth._budget_ms(60000) <= 2000
    with auth.time_limit(0.01):
        time.sleep(0.03)
        with pytest.raises(auth.LoginBlocked, match="did not finish within"):
            auth._budget_ms(1000)
    ev = threading.Event()
    ev.set()
    with auth.time_limit(100, ev):
        with pytest.raises(auth.LoginStopped):
            auth._budget_ms(1000)
    assert getattr(auth._limit, "v", None) is None                  # the limit ends with the block


def test_app_ready_inside_a_sign_in_does_not_wait_past_the_limit():
    from framework import auth
    waited = []

    class Loc:
        first = None

        def wait_for(self, state, timeout):
            waited.append(timeout)
            raise TimeoutError("not ready")
    Loc.first = Loc()

    class Page:
        def get_by_text(self, *a, **k):
            return Loc()
    with auth.time_limit(1.5):
        assert auth.app_ready(Page(), 60000) is False
    assert waited and waited[0] <= 1500


class _Ctx:
    def new_page(self):
        class P:
            def close(self):
                pass
        return P()


def test_sign_in_runs_under_a_time_limit_and_stop_ends_it(monkeypatch):
    from framework import auth
    seen = []

    def login(page):
        seen.append(getattr(auth._limit, "v", None))
        return "bp"
    monkeypatch.setattr(auth, "login", login)
    assert executor._sign_in(_Ctx(), lambda m: None) == "bp"
    assert seen[0] and seen[0][1] == executor.SIGN_IN_TRY_LIMIT

    stop = threading.Event()

    def stopped_login(page):
        stop.set()
        auth._budget_ms(1000)                       # the next wait inside the login sees the Stop
    monkeypatch.setattr(auth, "login", stopped_login)
    with pytest.raises(executor.Stopped):
        executor._sign_in(_Ctx(), lambda m: None, stop=stop)
    with pytest.raises(executor.Stopped):          # no new try once Stop was pressed
        executor._sign_in(_Ctx(), lambda m: None, stop=stop)

    logs = []
    n = []

    def flaky(page):
        n.append(1)
        if len(n) == 1:
            raise auth.LoginBlocked("Anjaan screen pe atke hain")
        return "bp2"
    monkeypatch.setattr(auth, "login", flaky)
    assert executor._sign_in(_Ctx(), logs.append) == "bp2"
    assert any("Signing in again, try 2" in m for m in logs)


def test_a_slow_header_after_sign_in_is_not_an_ended_session():
    calls = []

    def ready(page, ms):
        calls.append(ms)
        return ms >= 20000                      # not within 4 s, but within 20 s (busy server)

    class BP:
        class page:
            url = "https://books6.margbooks.com/dashboard"
    assert executor._session_alive(BP(), ready) is True and calls == [4000, 20000]

    class Out:
        class page:
            url = "https://margbooks.com/login/"
    assert executor._session_alive(Out(), lambda p, ms: False) is False


def test_run_screen_shows_the_sign_in_progress_while_no_step_runs():
    job = {"id": "R-n", "state": "running", "title": "TC · x (starting the browser…)", "total": 1, "done": 0,
           "steps": [], "current": None, "results": [], "seconds": 0, "log": ""}
    executor.JOBS["R-n"] = job
    try:
        executor._run_log(job, "Sign-in try 1 failed: Anjaan screen pe atke hain Trying once more…")
        executor._run_log(job, "  [dialog] OK: something")               # framework console noise is not shown
        assert executor.run_status("R-n")["note"].startswith("Sign-in try 1 failed")
    finally:
        executor.JOBS.pop("R-n", None)
    f = _fn(APP, "renderRun")
    assert "d.note" in f and "!!c" in f                     # the note is shown, and REC only while a case runs


# ================================================================ runs: Stop while saving

def test_saving_after_stop_does_not_say_all_steps_are_done():
    f = _fn(APP, "renderRun")
    assert "d.stopping ? 'Stopped. Saving the video" in f
    i = f.index("d.stopping ? 'Stopped. Saving")
    assert f.index("'All steps are done.") > i               # 'All steps are done' only when not stopped


# ================================================================ cases: /api/tests under load

def test_tests_list_is_encoded_once_and_gzipped(store_tmp, monkeypatch):   # noqa: F811
    from ui import store
    store.save(name="A", description="", module="sales", case_id="TC_ENC_X", steps=[{"action": "sleep", "value": "1"}])
    studio_tests._LIST.update(key=None, out=None, at=0.0)
    dumps = []
    real = json.dumps
    monkeypatch.setattr(studio_tests.json, "dumps", lambda *a, **k: (dumps.append(1), real(*a, **k))[1])
    raw, gz = studio_tests.list_tests_body()
    raw2, gz2 = studio_tests.list_tests_body()
    assert raw is raw2 and len(dumps) == 1                 # the second request reuses the bytes
    assert json.loads(gzip.decompress(gz)) == json.loads(raw)
    assert any(t["id"] == "TC_ENC_X" for t in json.loads(raw)["tests"])


def test_requests_during_a_check_get_the_last_list_instead_of_queueing(store_tmp, monkeypatch):   # noqa: F811
    studio_tests._LIST.update(key=None, out=None, at=0.0)
    first = studio_tests.list_tests()
    studio_tests._LIST["at"] = 0.0                          # the fresh time ran out
    with studio_tests._LIST_LOCK:                           # another request is checking right now
        t0 = time.time()
        assert studio_tests.list_tests() == first and time.time() - t0 < 1
        studio_tests.invalidate_list()                      # ... but after a save nobody gets the old list
        got = []
        t = threading.Thread(target=lambda: got.append(studio_tests.list_tests()))
        t.start()
        t.join(0.5)
        assert not got                                      # it waits for the check
    t.join(10)
    assert got


def test_api_tests_answers_gzipped_when_the_browser_accepts_it(srv, store_tmp):   # noqa: F811
    op = _login(srv, "qa1@qa.test")
    req = urllib.request.Request(srv + "/api/tests", headers={"Accept-Encoding": "gzip"})
    with op.open(req) as r:
        assert r.headers.get("Content-Encoding") == "gzip"
        assert "tests" in json.loads(gzip.decompress(r.read()))
    with op.open(urllib.request.Request(srv + "/api/tests")) as r:
        assert r.headers.get("Content-Encoding") is None and "tests" in json.loads(r.read())


# ================================================================ record: password in a re-formatted script

def test_single_quotes_rewrites_double_quoted_and_backtick_strings_only():
    assert script.single_quotes('await page.fill("a b");') == "await page.fill('a b');"
    assert script.single_quotes("await page.fill(`x`);") == "await page.fill('x');"
    assert script.single_quotes('await page.fill("it\'s");') == 'await page.fill("it\'s");'
    assert script.single_quotes("await page.fill(`${a}`);") == "await page.fill(`${a}`);"
    assert script.single_quotes("x('input[type=\"password\"]')") == "x('input[type=\"password\"]')"
    assert script.single_quotes('a(); // "keep" this') == 'a(); // "keep" this'


DQ = SAMPLE.replace("'", '"')


def test_double_quoted_pasted_login_becomes_login_page():
    p = recorder.paste(DQ)["code"]
    assert "Placeholder#Pass1" not in p and "qa.tester@example.com" not in p and "await login(page)" in p
    assert "accounts.margbooks.com" not in p and "Data Backup" in p
    assert "Placeholder#Pass1" not in studio_tests.redact_code(DQ, [])
    # Verify on such code in the editor (not pasted): the Must-fix login finding
    f = [x for x in verify._findings(DQ) if x.id == "login"]
    assert f and f[0].sev == "Must fix"
    assert "Placeholder#Pass1" not in verify.apply(DQ, ["login"])


def _links(n):
    return "".join(f"  await page.getByRole('link', {{ name: 'L{i}' }}).click();\n" for i in range(n))


LINK = "  await page.getByRole('link', { name: 'Login with password' }).click();\n"


@pytest.mark.parametrize("n", [0, 3, 4, 7])
@pytest.mark.parametrize("box", ["locator('#mat-input-1')", "locator('input').nth(1)"])
def test_password_through_a_css_locator_before_continue_is_removed(n, box):
    code = SAMPLE.replace(LINK, _links(n)).replace("getByRole('textbox').fill(", box + ".fill(")
    p = recorder.paste(code)["code"]
    assert "Placeholder#Pass1" not in p and "Placeholder#Pass1" not in studio_tests.redact_code(code, [])
    assert "Data Backup" in p


@pytest.mark.parametrize("n", [9, 12, 20])
def test_password_after_many_unknown_clicks_is_removed(n):
    code = SAMPLE.replace(LINK, _links(n))
    assert "Placeholder#Pass1" not in recorder.paste(code)["code"]
    assert "Placeholder#Pass1" not in studio_tests.redact_code(code, [])


def test_search_typed_after_login_and_a_page_load_stays():
    code = SAMPLE.replace("  await page.goto('https://books6.margbooks.com/mb/utillity-menu');",
                          "  await page.goto('https://books6.margbooks.com/mb/utillity-menu');\n"
                          "  await page.locator('#search').fill('Paracetamol');\n"
                          "  await page.getByRole('button', { name: 'Continue' }).click();")
    p = recorder.paste(code)["code"]
    assert "Placeholder#Pass1" not in p and "Paracetamol" in p


def test_verify_flags_a_css_password_before_continue_after_login_page():
    head = ("import { test } from '@playwright/test';\nimport { login } from '../helpers/mb';\n"
            "test('x', async ({ page }) => {\n  await login(page);\n")
    code = head + _links(10) + ("  await page.locator('#mat-input-1').fill('Secret#123');\n"
                                "  await page.getByRole('button', { name: 'Continue' }).click();\n});")
    f = [x for x in verify._findings(code) if x.id == "login"]
    assert f and f[0].sev == "Must fix" and "Secret#123" not in verify.apply(code, ["login"])
    # a form filled after a page step is a test step
    code2 = head + "  await page.goto('https://books6.margbooks.com/x');\n" + (
        "  await page.locator('#qty').fill('5');\n  await page.getByRole('button', { name: 'Continue' }).click();\n});")
    assert not [x for x in verify._findings(code2) if x.id == "login"]
    # a search box with Enter right after login(page) is not a password
    code3 = head + ("  await page.locator('#search').fill('Paracetamol');\n  await page.keyboard.press('Enter');\n"
                    "  await page.locator('#search').press('Enter');\n});")
    assert not [x for x in verify._findings(code3) if x.id == "login"]


# ================================================================ reports

def test_user_stopped_run_is_not_labelled_not_run():
    f = _fn(APP, "skipHead")
    assert "Stopped at step" in f and "'Not run'" in f
    assert "skipHead(r, st)" in _fn(APP, "openRun")


def test_passed_count_follows_the_corrected_steps(tmp_path):
    steps = [{"text": f"s{i + 1}", "status": "ok"} for i in range(6)]
    _run_row("R-0022", "Step 1 failed: use_company QA Pharma Distribution", 5, steps, str(tmp_path))
    with state.db() as c:
        c.execute("UPDATE runs SET passed=6 WHERE id='R-0022'")
    d = studio_tests.run_detail("R-0022")
    assert d["run"]["passed"] == 0 and [s["status"] for s in d["steps"]][:2] == ["Fail", "Skip"]
    row = next(r for r in studio_tests.list_runs()["runs"] if r["id"] == "R-0022")
    assert row["passed"] == 0
    assert "(0/6)" in studio_tests.report_html("R-0022")
    # a run whose stored failing step is right keeps its stored count
    _run_row("R-0023", "Step 2 failed: x", 1, [{"text": "a", "status": "ok"}, {"text": "b", "status": "bad"}], "")
    assert studio_tests.run_detail("R-0023")["run"]["passed"] == 1


# ================================================================ ops

def test_password_from_cmd_echo_pipe_has_no_trailing_space(monkeypatch):
    monkeypatch.setattr(accounts.sys, "stdin", io.StringIO("MyPassw0rd \r\n"))
    assert accounts._read_password("x", True) == "MyPassw0rd"
    assert "echo MyPassw0rd|" in accounts.__doc__


def test_server_drops_a_client_that_stops_sending(srv, monkeypatch):   # noqa: F811
    assert server.Handler.timeout and server.Handler.timeout <= 120
    monkeypatch.setattr(server.Handler, "timeout", 1)
    host, port = srv.replace("http://", "").split(":")
    s = socket.create_connection((host, int(port)), timeout=10)
    s.sendall(b"POST /api/auth/login HTTP/1.1\r\nHost: x\r\nX-Studio: 1\r\nContent-Length: 1000\r\n\r\n0123456789")
    t0 = time.time()
    data = s.recv(100)                       # the server closes the connection (no answer, or a short one)
    assert time.time() - t0 < 8 and (data == b"" or data.startswith(b"HTTP/"))
    s.close()
    s = socket.create_connection((host, int(port)), timeout=10)
    s.sendall(b"POST /api/auth/login HTTP/1.1\r\nHost: x\r\n")
    t0 = time.time()
    s.recv(100)
    assert time.time() - t0 < 8
    s.close()


def test_post_body_is_not_read_before_the_login_check(srv):   # noqa: F811
    host, port = srv.replace("http://", "").split(":")
    s = socket.create_connection((host, int(port)), timeout=10)
    s.sendall(b"POST /api/tests/save-draft HTTP/1.1\r\nHost: x\r\nX-Studio: 1\r\nContent-Length: 5000000\r\n\r\n")
    data = s.recv(4096)
    assert data.startswith(b"HTTP/1.0 401") or data.startswith(b"HTTP/1.1 401")
    s.close()
