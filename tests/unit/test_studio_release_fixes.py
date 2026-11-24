"""Release QA round 1: the issues the QA agents found in team-mode Test Studio, one test (or more) each.
No browser and no network: the browser player is a stub, the HTTP server runs on a free local port."""
from __future__ import annotations

import io
import json
import os
import socket
import threading
import time
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from ui_studio import accounts, executor, grammar, learn, memory, mode, recorder, server, state, tests as studio_tests
from ui_studio import verify

from tests.unit.test_studio_server_mode import _call, _client

LINES = ["Log in", "create sale bill", 'verify "Bill saved"']


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "studio_settings.json")
    monkeypatch.setattr(memory, "ALIASES_FILE", tmp_path / "aliases.json")
    memory._cache["stamp"] = None
    state.save_settings({"out_dir": str(tmp_path / "specs")})
    accounts._fails.clear()
    yield
    memory._cache["stamp"] = None


@pytest.fixture
def store_tmp(tmp_path, monkeypatch):
    from ui import store
    monkeypatch.setattr(store, "SAVED", tmp_path / "saved")
    (tmp_path / "saved").mkdir()
    monkeypatch.setattr(store, "list_all", lambda: __import__("framework.case_loader", fromlist=["x"]).load_all(tmp_path / "saved"))
    return tmp_path


@pytest.fixture
def srv(monkeypatch):
    monkeypatch.setattr(mode, "SERVER", True)
    monkeypatch.setattr(mode, "SECURE_COOKIE", False)
    s = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    accounts.create_user("boss@qa.test", "password123", "admin", "Boss")
    accounts.create_user("qa1@qa.test", "password123", "qa", "QA One")
    accounts.create_user("qa2@qa.test", "password123", "qa", "QA Two")
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown()


def _login(base, user):
    op = _client()
    assert _call(op, base, "/api/auth/login", {"username": user, "password": "password123"})[0] == 200
    return op


# ================================================================ auth

def test_disabled_admin_can_be_demoted_and_disabled_again():
    accounts.create_user("boss@qa.test", "password123", "admin")
    accounts.create_user("second@qa.test", "password123", "admin")
    accounts.update_user("second@qa.test", disabled=True)
    assert accounts.update_user("second@qa.test", role="qa")["role"] == "qa"           # not the last ACTIVE admin
    accounts.update_user("second@qa.test", role="admin")
    assert accounts.update_user("second@qa.test", disabled=True)["disabled"]
    with pytest.raises(accounts.AuthError, match="last admin"):                 # the one active admin stays
        accounts.update_user("boss@qa.test", role="qa")


def test_non_text_login_and_user_fields_are_refused_cleanly(srv):
    with pytest.raises(accounts.AuthError, match="Wrong username"):
        accounts.login(5, None)
    code, d, _ = _call(_client(), srv, "/api/auth/login", {"username": 5, "password": None})
    assert code == 401 and d["error"] == "Wrong username or password."
    ad = _login(srv, "boss@qa.test")
    code, d, _ = _call(ad, srv, "/api/users", {"username": "qa1@qa.test", "name": 12345})
    assert code == 400 and "text" in d["error"]
    code, _, _ = _call(ad, srv, "/api/users", {"create": True, "username": "qa9", "password": "password123", "name": 7})
    assert code == 400


def test_unknown_username_costs_the_same_password_check(monkeypatch):
    accounts.create_user("qa1@qa.test", "password123")
    seen = []
    real = accounts.check_password
    monkeypatch.setattr(accounts, "check_password", lambda pw, stored: seen.append(stored) or real(pw, stored))
    with pytest.raises(accounts.AuthError):
        accounts.login("ghost", "whatever")
    assert seen and seen[0].startswith("pbkdf2_sha256$")


def test_wrong_current_password_counts_toward_the_lockout():
    accounts.create_user("qa1@qa.test", "password123")
    for _ in range(accounts.MAX_FAILS):
        with pytest.raises(accounts.AuthError, match="not right"):
            accounts.change_own_password("qa1@qa.test", "wrong-one", "newpassword1")
    with pytest.raises(accounts.AuthError, match="Too many"):
        accounts.change_own_password("qa1@qa.test", "password123", "newpassword1")


def test_session_slides_and_the_cookie_is_sent_again(srv, monkeypatch):
    accounts.create_user("qa3@qa.test", "password123")
    tok, _ = accounts.login("qa3@qa.test", "password123")
    with state.db() as c:
        c.execute("UPDATE sessions SET expires=?", (time.time() + 3600,))
    info = {}
    assert accounts.session_user(tok, info) and info.get("slid")
    op = _login(srv, "qa1@qa.test")
    with state.db() as c:
        c.execute("UPDATE sessions SET expires=? WHERE username='qa1@qa.test'", (time.time() + 3600,))
    code, _, hdr = _call(op, srv, "/api/auth/state")
    assert code == 200 and "Max-Age=43200" in (hdr.get("Set-Cookie") or "")


def test_cli_mixed_case_names_and_password_from_stdin(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "stdin", io.StringIO("password123\n"))
    assert accounts._cli(["add", "Ops.Mixed@Example.com", "--admin", "--password-stdin", "--name", "Ops Person"]) == 0
    u = accounts.get_user("ops.mixed@example.com")
    assert u["username"] == "ops.mixed@example.com" and u["role"] == "admin" and u["name"] == "Ops Person"
    monkeypatch.setattr(sys, "stdin", io.StringIO("password456\n"))         # not a console: read from stdin
    assert accounts._cli(["reset", "OPS.MIXED@example.com"]) == 0
    accounts.login("ops.mixed@example.com", "password456")
    accounts.create_user("boss2@qa.test", "password123", "admin")
    assert accounts._cli(["disable", "OPS.MIXED@EXAMPLE.COM"]) == 0 and accounts.get_user("ops.mixed@example.com")["disabled"]
    assert accounts._cli(["role", "ops.mixed@example.com", "qa"]) == 0
    assert accounts.get_user("ops.mixed@example.com")["role"] == "qa"
    monkeypatch.setattr(sys, "stdin", io.StringIO("password789\n"))
    assert accounts._cli(["add", "notanemail", "--password-stdin"]) == 1          # a login must be an e-mail


def test_login_email_can_be_changed_and_history_follows(monkeypatch):
    from ui_studio import state
    accounts.create_user("old.name@qa.test", "password123", "admin")
    accounts.create_user("boss@qa.test", "password123", "admin")
    tok, _ = accounts.login("old.name@qa.test", "password123")
    with state.db() as c:
        c.execute("INSERT INTO runs(id,test_id,result,run_by,ts) VALUES('R-1','T','Pass','old.name@qa.test',0)")
    u = accounts.change_email("old.name@qa.test", "New.Name@QA.test")
    assert u["username"] == "new.name@qa.test" and accounts.session_user(tok) is None     # logged out
    accounts.login("new.name@qa.test", "password123")
    with state.db() as c:
        assert c.execute("SELECT run_by FROM runs WHERE id='R-1'").fetchone()[0] == "new.name@qa.test"
    with pytest.raises(accounts.AuthError):
        accounts.change_email("new.name@qa.test", "boss@qa.test")                    # taken
    with pytest.raises(accounts.AuthError):
        accounts.change_email("new.name@qa.test", "not an email")


# ================================================================ HTTP hardening

def _raw(base, data: bytes) -> bytes:
    host, port = base.replace("http://", "").split(":")
    s = socket.create_connection((host, int(port)), timeout=20)
    s.sendall(data)
    s.shutdown(socket.SHUT_WR)
    out = b""
    while True:
        b = s.recv(65536)
        if not b:
            break
        out += b
    s.close()
    return out


def test_healthz_shows_counts_only_and_answers_head(srv):
    executor.JOBS["R-h"] = {"id": "R-h", "kind": "run", "state": "running", "title": "TC_X · secret test",
                            "_owner": {"username": "qa1@qa.test"}}
    try:
        code, d, _ = _call(_client(), srv, "/healthz")
        assert code == 200 and d["ok"] and "jobs" not in d and "qa1@qa.test" not in json.dumps(d) and d["running"] == 1
        head = _raw(srv, b"HEAD /healthz HTTP/1.1\r\nHost: x\r\n\r\n")
        assert head.startswith(b"HTTP/1.0 200") and b"X-Frame-Options: DENY" in head
        opt = _raw(srv, b"OPTIONS /api/state HTTP/1.1\r\nHost: x\r\n\r\n")
        assert opt.startswith(b"HTTP/1.0 405") and b"nosniff" in opt and b"application/json" in opt
    finally:
        executor.JOBS.pop("R-h", None)


def test_negative_length_and_non_object_bodies_are_400(srv):
    big = b'{"username":"x","password":"' + b"a" * 200000 + b'"}'
    out = _raw(srv, b"POST /api/auth/login HTTP/1.1\r\nHost: x\r\nX-Studio: 1\r\nContent-Length: -1\r\n\r\n" + big)
    assert out.startswith(b"HTTP/1.0 400")
    for body in ([], "x", [1, 2]):
        assert _call(_client(), srv, "/api/auth/login", body)[0] == 400
    qa = _login(srv, "qa1@qa.test")
    assert _call(qa, srv, "/api/write/check", [1, 2])[0] == 400


def test_oversize_body_gets_a_413_reply_not_a_reset(srv, monkeypatch):
    monkeypatch.setattr(server, "MAX_BODY", 1000)
    n = 50000
    out = _raw(srv, b"POST /api/verify HTTP/1.1\r\nHost: x\r\nX-Studio: 1\r\nContent-Length: " + str(n).encode()
               + b"\r\n\r\n" + b"x" * n)
    assert out.startswith(b"HTTP/1.0 413") and b"too large" in out


def test_qa_cannot_read_shared_settings(srv):
    assert _call(_login(srv, "qa1@qa.test"), srv, "/api/settings")[0] == 403
    assert _call(_login(srv, "boss@qa.test"), srv, "/api/settings")[0] == 200


def test_admin_test_login_waits_for_a_run_with_the_same_margbooks_user(srv, monkeypatch):
    from ui import envs
    monkeypatch.setattr(envs, "apply_active", lambda: {"name": "e", "user": "shared@mb"})
    seen = []
    monkeypatch.setattr(server, "test_login", lambda env=None: seen.append(dict(executor._busy["mb"])) or {"ok": True})
    ad = _login(srv, "boss@qa.test")
    assert _call(ad, srv, "/api/settings/test-login", {})[0] == 200
    assert seen and "shared@mb" in seen[0]          # it held the shared user's slot while it logged in


# ================================================================ runs

def test_slot_reason_names_the_other_qa_and_timer_skips_the_wait(monkeypatch):
    monkeypatch.setattr(mode, "MAX_BROWSERS", 3)
    a = {"_owner": {"mb_user": "same@mb", "username": "qa4"}}
    b = {"_owner": {"mb_user": "same@mb", "username": "qa5"}, "title": "Queued", "next_title": "TC_1 · x"}
    go = threading.Event()

    def hold():
        with executor._slot(a, {"steps": []}):
            go.wait(5)
    t = threading.Thread(target=hold)
    t.start()
    time.sleep(0.1)
    t2 = threading.Thread(target=lambda: executor._slot(b, {"steps": []}).__enter__())
    t2.start()
    time.sleep(0.3)
    assert b["waiting"] == "another run (qa4) is using the same MargBooks login"
    assert executor.run_seconds(b) == 0
    go.set()
    t.join(5)
    t2.join(10)
    assert "waiting" not in b and b["title"] == "TC_1 · x" and b["waited"] >= 0.2
    assert executor.run_seconds(b) < 1          # counting from when it got the browser, not from the queue
    executor._busy.update(n=0, mb={}, co=set())


def _fake_cases(monkeypatch, n=3):
    cases = [{"id": f"TC_{i}", "display_id": f"TC_{i}", "name": f"case {i}", "module": "Sale", "author": "a",
              "steps": [{"action": "note", "value": "x"}], "destructive": False} for i in range(n)]
    monkeypatch.setattr(studio_tests, "load_cases", lambda ids: cases)
    return cases


def test_a_run_can_be_stopped_and_the_rest_is_not_run(monkeypatch):
    _fake_cases(monkeypatch)
    played = []
    started = threading.Event()

    def play(cases, opts, on_step, on_log, stop=None):
        played.append(cases[0]["id"])
        started.set()
        stop.wait(5)                                     # a long step; Stop ends it
        return [{"outcome": "skipped", "error": "Stopped by the user at step 1.", "failed_step": -1, "shots": []}]
    rid = "R-stop1"
    executor.JOBS[rid] = {"id": rid, "kind": "run", "state": "queued", "title": "Queued", "total": 0, "done": 0,
                          "steps": [], "current": None, "results": [], "seconds": 0, "who": "qa", "ids": ["a"],
                          "opts": {}, "dir": "x", "log": "", "_owner": None, "created": time.time(),
                          "_stop": threading.Event()}
    t = threading.Thread(target=executor._run_thread, args=(rid, play))
    t.start()
    assert started.wait(5)
    assert executor.stop_run(rid, "qa1@qa.test")["state"] == "stopping"
    t.join(10)
    job = executor.JOBS.pop(rid)
    assert played == ["TC_0"] and job["state"] == "stopped" and "2 tests not run" in job["title"]
    assert job["results"][0]["result"] == "Skip"


def test_live_runs_are_found_again_after_a_reload():
    executor.JOBS["R-l1"] = {"id": "R-l1", "kind": "run", "state": "running", "_owner": {"username": "qa1@qa.test"},
                             "created": 1, "opts": {"video": False}}
    executor.JOBS["R-l2"] = {"id": "R-l2", "kind": "run", "state": "running", "_owner": {"username": "qa2@qa.test"},
                             "created": 2, "opts": {}}
    try:
        mine = executor.live_runs({"username": "qa1@qa.test", "role": "qa"})
        assert [r["id"] for r in mine] == ["R-l1"] and mine[0]["video"] is False
        assert [r["id"] for r in executor.live_runs(None)] == ["R-l2", "R-l1"]
    finally:
        executor.JOBS.pop("R-l1"), executor.JOBS.pop("R-l2")


def test_run_status_says_why_it_waits():
    executor.JOBS["R-w"] = {"id": "R-w", "kind": "run", "state": "running", "title": "Waiting: x", "total": 1,
                            "done": 0, "steps": [], "current": None, "results": [], "seconds": 0, "log": "",
                            "waiting": "all browsers of the Studio are busy"}
    executor.JOBS["r-w"] = {"id": "r-w", "kind": "replay", "state": "running", "attempt": 1, "max": 1, "aiFixes": 0,
                            "steps": [], "err": None, "code": "", "fixedLines": [], "tokens": {}, "giveUp": False,
                            "log": "", "waiting": "all browsers of the Studio are busy"}
    try:
        d = executor.run_status("R-w")
        assert d["state"] == "queued" and d["waiting"] == "all browsers of the Studio are busy"
        r = executor.replay_status("r-w")
        assert r["state"] == "queued" and r["waiting"]
    finally:
        executor.JOBS.pop("R-w"), executor.JOBS.pop("r-w")


def test_failed_step_is_the_step_the_error_names():
    steps = [{"action": "use_company", "value": "QA"}, {"action": "sleep", "value": "1"},
             {"action": "click", "target": "x", "always": True}]
    assert executor.failed_index("Step 1 failed: use_company QA\nboom", {"i": 10, "fail": 10}, 3) == 0
    assert executor.failed_index("no number here", {"i": 1, "fail": 1}, 3) == 1
    assert executor.failed_index("Step 79 failed", {"i": 2}, 3) == 2          # out of range: fall back
    assert executor.step_index(steps, steps[1], 0) == 1
    assert executor.step_index(steps, {**steps[2], "always": False}, 0) == 2  # a clean-up copy


def test_reports_count_fail_only_and_show_who_ran_it():
    accounts.create_user("qa2@qa.test", "password123", "qa", "QA Tester 2")
    with state.db() as c:
        for i, (res, by) in enumerate([("Pass", "qa2@qa.test"), ("Fail", "qa2@qa.test"), ("Skip", ""), ("Blocked", "")]):
            c.execute("INSERT INTO runs(id,test_id,name,module,author,at,passed,total,result,err,fail_at,steps,dir,"
                      "ai_fixes,ts,run_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (f"R-000{i}", "TC_1", "n", "Sale", "unknown", "now", 0, 1, res, "", -1, "[]", "d", 0, i, by))
    d = studio_tests.list_runs()
    assert d["kpis"]["failed"] == 1 and d["kpis"]["passed"] == 1 and d["kpis"]["other"] == 2
    assert d["kpis"]["testers"] == 1
    row = next(r for r in d["runs"] if r["id"] == "R-0001")
    assert row["runBy"] == "qa2@qa.test" and row["runByName"] == "QA Tester 2"
    assert studio_tests.run_detail("R-0001")["run"]["runByName"] == "QA Tester 2"


def test_spec_of_a_missing_test_is_404(srv):
    with pytest.raises(KeyError):
        studio_tests.spec_text("TC_DOES_NOT_EXIST")
    qa = _login(srv, "qa1@qa.test")
    code, d, _ = _call(qa, srv, "/api/download?kind=spec&id=TC_DOES_NOT_EXIST")
    assert code == 404 and "does not exist" in d["error"]


# ================================================================ traces

def test_trace_zip_is_scrubbed_of_passwords(tmp_path):
    tz = tmp_path / "trace.zip"
    with zipfile.ZipFile(tz, "w") as z:
        z.writestr("trace.trace", '{"type":"action","method":"fill","params":{"value":"S3cret!pw"}}\n')
        z.writestr("resources/abc.json", '{"userid":"a@b.c","password":"S3cret!pw"}')
        z.writestr("resources/def.json", '{"userid":"a@b.c","password":"other-unknown-pw"}')
        z.writestr("resources/shot.jpeg", b"\xff\xd8S3cret!pw")
    assert executor.scrub_trace(tz, ["S3cret!pw"])
    with zipfile.ZipFile(tz) as z:
        text = b"".join(z.read(n) for n in z.namelist() if not n.endswith(".jpeg"))
        assert b"S3cret!pw" not in text and b"other-unknown-pw" not in text and b'"password":"***"' in text
        assert z.read("resources/shot.jpeg") == b"\xff\xd8S3cret!pw"           # images are not rewritten
    assert not executor.scrub_trace(tz, ["S3cret!pw"])                         # nothing left to remove


def test_trace_download_is_scrubbed_with_every_saved_margbooks_password(tmp_path):
    accounts.create_user("qa7@qa.test", "password123")
    accounts.set_margbooks_login("qa7@qa.test", "qa7@mb", "Qa7-Pass!")
    d = tmp_path / "run"
    d.mkdir()
    with zipfile.ZipFile(d / "trace.zip", "w") as z:
        z.writestr("trace.trace", '{"params":{"value":"Qa7-Pass!"}}')
    with state.db() as c:
        c.execute("INSERT INTO runs(id,test_id,name,module,author,at,passed,total,result,err,fail_at,steps,dir,"
                  "ai_fixes,ts) VALUES('R-0009','TC_1','n','Sale','a','now',0,1,'Fail','',0,'[]',?,0,1)", (str(d),))
    data = studio_tests.trace_bytes("R-0009")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert b"Qa7-Pass!" not in z.read("trace.trace")


# ================================================================ write / save

def test_resave_updates_the_same_test_and_keeps_its_author(store_tmp):
    from ui_studio import script
    code = script.generate("Smoke", "Sale", "QA Four", LINES)["code"]
    a = studio_tests.save(code, "Smoke", "Sale", "High", "first", "QA Four", "written", LINES)
    b = studio_tests.save(code, "Smoke renamed", "Sale", "High", "second@qa.test", "QA One", "written", LINES, tid=a["id"])
    assert b["id"] == a["id"] and b["author"] == "QA Four" and b["updated"]
    assert [t["id"] for t in studio_tests.list_tests() if t["id"].startswith("TC-")] == [a["id"]]
    assert not Path(a["spec"]).exists() and Path(b["spec"]).exists()          # renamed: one spec file


def test_save_draft_keeps_description_priority_and_spec(store_tmp):
    from ui_studio import script
    import yaml
    code = script.generate("Smoke", "Sale", "QA Four", LINES)["code"]
    a = studio_tests.save(code, "Smoke", "Sale", "High", "QA4 smoke", "QA Four", "written", LINES)
    r = studio_tests.save_draft(a["id"], "Smoke", "Sale", "Someone Else", LINES + ['verify "Sale"'])
    assert r["id"] == a["id"] and r["author"] == "QA Four"
    case = yaml.safe_load(open(a["yaml"], encoding="utf-8"))[0]
    assert case["expected"] == ["QA4 smoke"] and "priority-high" in case["tags"] and "draft-lines" not in case["tags"]
    assert "Created by QA Four" in case["preconditions"][0]
    m = studio_tests._meta(a["id"])
    assert m["priority"] == "High" and m["description"] == "QA4 smoke" and m["spec_file"]
    assert "Sale" in open(m["spec_file"], encoding="utf-8").read().split("verify", 1)[-1] or "Sale" in m["code"]


def test_only_the_author_or_an_admin_changes_a_saved_test(srv, store_tmp):
    from ui_studio import script
    code = script.generate("Mine", "Sale", "QA One", LINES)["code"]
    a = studio_tests.save(code, "Mine", "Sale", "Medium", "", "QA One", "written", LINES)
    qa2 = _login(srv, "qa2@qa.test")
    code2, d, _ = _call(qa2, srv, "/api/tests/save-draft", {"id": a["id"], "name": "x", "module": "Sale", "lines": LINES})
    assert code2 == 403 and "QA One" in d["error"]
    assert _call(qa2, srv, "/api/save", {"id": a["id"], "code": code, "name": "x", "module": "Sale"})[0] == 403
    qa1 = _login(srv, "qa1@qa.test")
    code3, d, _ = _call(qa1, srv, "/api/tests/save-draft", {"id": a["id"], "name": "Mine", "module": "Sale", "lines": LINES})
    assert code3 == 200 and d["id"] == a["id"] and d["author"] == "QA One"


def test_write_check_accepts_null_lines():
    r = grammar.check([None, 5, "Log in"])
    assert r["results"][0]["status"] == "empty" and r["results"][2]["status"] == "ok"
    with pytest.raises(ValueError):
        grammar.check("not a list")


# ================================================================ record (paste)

PASTED = """import { test, expect } from '@playwright/test';

test('x', async ({ page }) => {
  await page.goto('https://accounts.margbooks.com/login');
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).fill('qa.tester@example.com');
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).press('Enter');
  await page.getByRole('textbox').click();
  await page.getByRole('textbox').fill('Placeholder#Pass1');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.goto('https://books6.margbooks.com/mb/utillity-menu');
  await expect(page.getByText('Data Backup')).toBeVisible();
});"""


def test_pasted_code_loses_its_login_and_password():
    r = recorder.paste(PASTED, ["My-Own-Pw"])
    assert "Placeholder#Pass1" not in r["code"] and "qa.tester@example.com" not in r["code"]
    assert "await login(page)" in r["code"] and r["actions"] >= 2
    assert "***" in recorder.paste(PASTED.replace("Data Backup", "My-Own-Pw"), ["My-Own-Pw"])["code"]


def test_python_or_garbage_paste_is_refused_with_a_way_out():
    with pytest.raises(ValueError, match="--target=playwright-test"):
        recorder.paste("from playwright.sync_api import Playwright\ndef run(playwright):\n    page.goto('https://x')\n")
    with pytest.raises(ValueError, match="not Playwright TypeScript"):
        recorder.paste("hello this is not code\nasdf qwer")
    f = verify.run("hello this is not code")["findings"]
    assert f and f[0]["id"] == "no-actions" and f[0]["sev"] == "Must fix" and f[0]["manual"]


def test_saved_test_never_keeps_a_password(store_tmp):
    from ui_studio import script
    r = studio_tests.save(PASTED, "Paste", "Masters", "Medium", "", "QA Five", "record", extra_secrets=["Data Backup"])
    text = open(r["spec"], encoding="utf-8").read()
    assert "Placeholder#Pass1" not in text and "await login(page)" in text
    assert "Placeholder#Pass1" not in (studio_tests._meta(r["id"])["code"] or "")


def test_paste_endpoint(srv):
    qa = _login(srv, "qa1@qa.test")
    code, d, _ = _call(qa, srv, "/api/record/paste", {"code": PASTED})
    assert code == 200 and "Placeholder#Pass1" not in d["code"]
    assert _call(qa, srv, "/api/record/paste", {"code": "garbage"})[0] == 400


# ================================================================ learn / teach / ops

def test_read_code_refuses_a_bad_folder_in_english_and_saves_nothing():
    with pytest.raises(ValueError) as e:
        learn.read_code("D:/no/such/folder_qa_learn", "")
    assert "was not found" in str(e.value) and "WinError" not in str(e.value)
    assert state.load_settings()["web_dir"] == ""


def test_teach_checks_screen_and_field_and_can_be_undone():
    with pytest.raises(ValueError, match="no field"):
        memory.teach("zzbogus", "Sale Bill", "NoSuchFieldQA")
    with pytest.raises(ValueError, match="no screen"):
        memory.teach("zzbogus", "No Such Screen QA", "X")
    memory.teach("discout", "Sale Bill", "Disc 1.%")
    assert "Sale Bill::discout" in memory.taught()
    assert memory.untaught("discout", "Sale Bill") and "Sale Bill::discout" not in memory.taught()
    assert not memory.untaught("discout", "Sale Bill")


def test_untaught_is_admin_only(srv):
    assert _call(_login(srv, "qa1@qa.test"), srv, "/api/write/untaught", {"term": "x", "screen": "Sale Bill"})[0] == 403


def test_cleanup_keeps_young_folders_and_zero_means_forever(tmp_path):
    old, young = tmp_path / "run_old", tmp_path / "run_young"
    old.mkdir()
    young.mkdir()
    t = time.time() - 40 * 86400
    os.utime(old, (t, t))
    assert server.cleanup_old_runs_once(tmp_path, 0) == [] and old.exists()
    assert server.cleanup_old_runs_once(tmp_path, -1) == [] and old.exists()
    assert server.cleanup_old_runs_once(tmp_path, 30) == ["run_old"] and young.exists()
