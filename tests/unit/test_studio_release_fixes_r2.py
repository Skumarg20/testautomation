"""Release QA round 2: the issues the QA agents found in team-mode Test Studio, one test (or more) each.
No browser and no network: the browser player and the run process are stubs, the HTTP server runs on a free port."""
from __future__ import annotations

import io
import json
import sqlite3
import threading
import time
import zipfile
from pathlib import Path

import pytest

from ui_studio import accounts, executor, memory, mode, recorder, server, state, tests as studio_tests
from ui_studio import verify, worker

from tests.unit.test_studio_release_fixes import srv, store_tmp, _login, LINES   # noqa: F401  (fixtures)
from tests.unit.test_studio_server_mode import _call

APP = (Path(__file__).resolve().parents[2] / "ui_studio" / "app.html").read_text(encoding="utf-8")


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


def _fn(src: str, name: str) -> str:
    """The text of one JS function of app.html."""
    i = src.index(f"function {name}(")
    j = src.index("\nfunction ", i + 10) if "\nfunction " in src[i + 10:] else len(src)
    k = src.find("\nasync function ", i + 10)
    return src[i: min(j, k) if k > 0 else j]


# ================================================================ auth: login under load

def test_db_has_no_process_wide_lock_and_reads_do_not_wait_for_a_writer():
    accounts.create_user("qa1@qa.test", "password123", "qa")
    assert not hasattr(state, "_lock")
    # a run process holds the write lock (an open write transaction) for a while
    other = sqlite3.connect(state.DB, timeout=30)
    other.execute("BEGIN IMMEDIATE")
    other.execute("INSERT INTO ai_cache VALUES('k','v',0)")
    try:
        t0 = time.time()
        assert accounts.get_user("qa1@qa.test")["username"] == "qa1@qa.test"            # login/session reads are not blocked
        token = None
        with state.db() as c:
            c.execute("SELECT COUNT(*) FROM users").fetchone()
        assert time.time() - t0 < 3
    finally:
        other.rollback()
        other.close()
    token, _ = accounts.login("qa1@qa.test", "password123")
    assert accounts.session_user(token)["username"] == "qa1@qa.test"
    with state.db() as c:
        assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_tables_are_created_once_per_database_not_on_every_query(monkeypatch):
    calls = []
    real = state._init
    monkeypatch.setattr(state, "_init", lambda key: (calls.append(key), real(key)))
    for _ in range(5):
        accounts.count_users()
    assert len(calls) == 1


def test_two_threads_use_the_db_at_the_same_time():
    accounts.create_user("qa1@qa.test", "password123", "qa")
    inside = threading.Event()
    done = []

    def slow():
        with state.db() as c:
            c.execute("SELECT 1").fetchone()
            inside.set()
            time.sleep(0.8)

    t = threading.Thread(target=slow)
    t.start()
    inside.wait(5)
    t0 = time.time()
    accounts.get_user("qa1@qa.test")
    done.append(time.time() - t0)
    t.join()
    assert done[0] < 0.5                       # the old global lock made this wait for the slow block


def test_login_button_shows_progress_and_cannot_be_clicked_twice():
    f = _fn(APP, "doLogin")
    assert "b.disabled = true" in f and "Logging in" in f and "b.disabled = false" in f


# ================================================================ runs

def test_run_screen_resumes_the_live_run_before_any_early_return():
    f = _fn(APP, "renderRunList")
    assert f.index("resumeRun()") < f.index("Pick a module above")
    assert f.index("resumeRun()") < f.index("No test cases yet")


def test_second_run_in_the_same_tab_says_why():
    f = _fn(APP, "runTests")
    assert "if (running) { toast(" in f
    i = APP.index("closest('[data-csrun]')")
    assert "if (running) { toast(" in APP[i: i + 300]


def test_worker_stop_file_sets_the_stop_event(tmp_path):
    f = tmp_path / "stop"
    ev = worker.stop_event(str(f), poll=0.05)
    time.sleep(0.15)
    assert not ev.is_set()
    f.write_text("stop")
    assert ev.wait(2)
    assert not worker.stop_event(None).is_set()


def test_stop_signals_the_worker_and_kills_only_after_the_grace(monkeypatch, tmp_path):
    """Team mode: Stop must not kill the run process at once, so its clean-up steps and setting undo run."""
    import subprocess
    monkeypatch.setattr(executor, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(executor, "STOP_GRACE", 5)
    seen = {}

    class P:
        def __init__(self, *a, **k):
            self.env = k["env"]
            self.stdin = io.StringIO()
            self.returncode = None
            self.killed = False
            seen["p"] = self

        @property
        def stdout(self):
            stop_file = Path(self.env["STUDIO_STOP_FILE"])
            yield '@@STUDIO@@ {"ev": "step", "ci": 0, "si": 0, "status": "ok", "secs": 1, "shot": null}\n'
            for _ in range(100):                         # the worker sees the file, runs its clean-up, ends
                if stop_file.exists():
                    break
                time.sleep(0.05)
            seen["file_seen"] = stop_file.exists()
            yield '@@STUDIO@@ {"ev": "log", "m": "CLEANUP ran"}\n'
            yield '@@STUDIO@@ {"ev": "result", "results": [{"outcome": "skipped"}]}\n'
            self.returncode = 0

        def poll(self):
            return self.returncode

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(subprocess, "Popen", P)
    stop = threading.Event()
    logs = []
    threading.Timer(0.2, stop.set).start()
    res = executor._play_isolated([{"id": "X", "steps": []}], {}, lambda *a: None, logs.append,
                                  {"username": "qa1@qa.test", "mb_user": "u", "mb_password": "p"}, stop)
    assert res == [{"outcome": "skipped"}]
    assert seen["file_seen"] and not seen["p"].killed and "CLEANUP ran" in logs
    assert not list(tmp_path.glob(".stop-*"))                      # the stop file is removed


def test_queue_is_first_come_first_served(monkeypatch):
    monkeypatch.setattr(mode, "MAX_BROWSERS", 3)
    holder = {"_owner": {"mb_user": "u1", "username": "qa2@qa.test"}}
    order = []
    release = threading.Event()

    def hold():
        with executor._slot(holder, {"steps": []}):
            release.wait(5)

    def run(tag, delay):
        time.sleep(delay)
        job = {"_owner": {"mb_user": "u1", "username": "qa2@qa.test"}}
        with executor._slot(job, {"steps": []}):
            order.append(tag)
            time.sleep(0.05)

    t0 = threading.Thread(target=hold)
    t0.start()
    time.sleep(0.1)
    ts = [threading.Thread(target=run, args=(f"r{i}", 0.05 * i)) for i in range(4)]
    for t in ts:
        t.start()
    time.sleep(0.5)
    release.set()
    for t in [t0] + ts:
        t.join(30)
    assert order == ["r0", "r1", "r2", "r3"]
    assert executor._busy["n"] == 0 and not executor._waiting


def test_saving_phase_is_shown_after_the_last_step():
    job = {"state": "running", "title": "x", "total": 1, "done": 0, "steps": [], "current": None, "results": [],
           "seconds": 0, "log": ""}
    executor.JOBS["R-phase"] = job
    try:
        executor._run_log(job, executor.SAVING_MSG + "…")
        assert executor.run_status("R-phase")["phase"] == "saving"
        job["state"] = "done"
        assert executor.run_status("R-phase")["phase"] == ""
    finally:
        executor.JOBS.pop("R-phase", None)
    assert "d.phase === 'saving'" in APP


# ================================================================ cases: /api/tests after a save

def _case_yaml(cid: str, title: str = "T") -> str:
    return f"- id: {cid}\n  module: sales\n  title: {title}\n  steps:\n  - action: sleep\n    value: '1'\n"


def test_case_loader_reparses_only_the_changed_file(tmp_path, monkeypatch):
    from framework import case_loader
    monkeypatch.setattr(case_loader, "_DISK", tmp_path / "cache" / "cases.pkl")
    monkeypatch.setattr(case_loader, "_CACHE", {})
    d = tmp_path / "cases"
    d.mkdir()
    for i in range(20):
        (d / f"c{i}.yaml").write_text(_case_yaml(f"C{i}"), encoding="utf-8")
    parsed = []
    real = case_loader._parse_file
    monkeypatch.setattr(case_loader, "_parse_file", lambda folder, f: (parsed.append(f.name), real(folder, f))[1])
    assert len(case_loader.load_all(d)) == 20 and len(parsed) == 20
    parsed.clear()
    (d / "c3.yaml").write_text(_case_yaml("C3", "changed title"), encoding="utf-8")
    cases = case_loader.load_all(d)
    assert parsed == ["c3.yaml"] and next(c for c in cases if c.id == "C3").title == "changed title"
    # a new process (empty memory cache) reads the per-file cache from disk: nothing is parsed again
    monkeypatch.setattr(case_loader, "_CACHE", {})
    parsed.clear()
    assert len(case_loader.load_all(d)) == 20 and parsed == []
    (d / "c4.yaml").unlink()
    assert len(case_loader.load_all(d)) == 19
    (d / "dup.yaml").write_text(_case_yaml("C1"), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        case_loader.load_all(d)


def test_concurrent_requests_during_a_rebuild_parse_once(tmp_path, monkeypatch):
    from framework import case_loader
    monkeypatch.setattr(case_loader, "_DISK", tmp_path / "cache" / "cases.pkl")
    monkeypatch.setattr(case_loader, "_CACHE", {})
    d = tmp_path / "cases"
    d.mkdir()
    (d / "a.yaml").write_text(_case_yaml("A"), encoding="utf-8")
    parsed = []
    real = case_loader._parse_file

    def slow(folder, f):
        parsed.append(f.name)
        time.sleep(0.3)
        return real(folder, f)
    monkeypatch.setattr(case_loader, "_parse_file", slow)
    ts = [threading.Thread(target=case_loader.load_all, args=(d,)) for _ in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(10)
    assert parsed == ["a.yaml"]


def test_list_tests_is_built_once_until_something_changes(store_tmp, monkeypatch):
    from ui_studio import script
    code = script.generate("Smoke", "Sale", "QA Four", LINES)["code"]
    studio_tests.save(code, "Smoke", "Sale", "High", "d", "QA Four", "written", LINES)
    builds = []
    real = studio_tests._build_list
    monkeypatch.setattr(studio_tests, "_build_list", lambda *a: (builds.append(1), real(*a))[1])
    studio_tests._LIST.update(key=None, out=None)
    a = studio_tests.list_tests()
    b = studio_tests.list_tests()
    assert a == b and len(builds) == 1
    studio_tests.save(code, "Smoke 2", "Sale", "Low", "d", "QA Four", "written", LINES)
    c = studio_tests.list_tests()
    assert len(builds) == 2 and len([t for t in c if t["id"].startswith("TC-")]) == 2


# ================================================================ write: priority and description

def test_resave_form_gets_the_opened_tests_priority_and_description(store_tmp):
    from ui_studio import script
    code = script.generate("Smoke", "Sale", "QA Four", LINES)["code"]
    a = studio_tests.save(code, "Smoke", "Sale", "High", "R2 desc keep me", "QA Four", "written", LINES)
    o = studio_tests.open_test(a["id"])
    assert o["priority"] == "High" and o["description"] == "R2 desc keep me"
    f = _fn(APP, "renderRecord")
    assert "<option selected>Medium</option>" not in f and "cur.description" in f and "cur.priority" in f
    assert "priority: d.priority, description: d.description" in APP


def test_chosen_priority_is_written_and_listed(store_tmp):
    import yaml
    from ui_studio import script
    code = script.generate("Smoke", "Sale", "QA Four", LINES)["code"]
    a = studio_tests.save(code, "Smoke", "Sale", "High", "d", "QA Four", "written", LINES)
    assert yaml.safe_load(open(a["yaml"], encoding="utf-8"))[0]["priority"] == "p1"
    b = studio_tests.save(code, "Other", "Sale", "Low", "d", "QA Four", "written", LINES)
    by = {t["id"]: t["priority"] for t in studio_tests.list_tests()}
    assert by[a["id"]] == "p1" and by[b["id"]] == "p3"
    # an older file that still says p2: the list shows the priority stored for the test
    p = Path(a["yaml"])
    p.write_text(p.read_text(encoding="utf-8").replace("priority: p1", "priority: p2"), encoding="utf-8")
    assert {t["id"]: t["priority"] for t in studio_tests.list_tests()}[a["id"]] == "p1"


# ================================================================ record: password after an unknown login step

SAMPLE = """import { test, expect } from '@playwright/test';

test('QA5 record', async ({ page }) => {
  await page.goto('https://books6.margbooks.com/');
  await page.goto('https://accounts.margbooks.com/login');
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).click();
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).fill('qa.tester@example.com');
  await page.getByRole('textbox', { name: 'Email address or mobile number' }).press('Enter');
  await page.getByRole('link', { name: 'Login with password' }).click();
  await page.getByRole('textbox').fill('Placeholder#Pass1');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.goto('https://books6.margbooks.com/mb/utillity-menu');
  await expect(page.getByText('Data Backup')).toBeVisible();
});"""


def test_password_after_an_unknown_login_step_is_removed_on_paste_and_save():
    p = recorder.paste(SAMPLE)["code"]
    assert "Placeholder#Pass1" not in p and "await login(page)" in p and "Login with password" not in p
    assert "utillity-menu" in p and "Data Backup" in p                        # the test itself stays
    assert "Placeholder#Pass1" not in studio_tests.redact_code(SAMPLE, [])


def test_login_block_does_not_swallow_test_steps_after_the_login():
    from ui_studio import script
    code = SAMPLE.replace("  await page.getByRole('link', { name: 'Login with password' }).click();\n", "")
    code = code.replace("  await page.goto('https://books6.margbooks.com/mb/utillity-menu');",
                        "  await page.getByRole('link', { name: 'Sale' }).click();\n"
                        "  await page.getByRole('link', { name: 'Bill' }).click();")
    ls = code.split("\n")
    kept = [ls[i] for i in range(len(ls)) if i not in script.login_block(code)]
    assert any("name: 'Sale'" in x for x in kept) and any("name: 'Bill'" in x for x in kept)


def test_verify_flags_a_password_left_after_login_page():
    code = ("import { test } from '@playwright/test';\nimport { login } from '../helpers/mb';\n"
            "test('x', async ({ page }) => {\n  await login(page);\n"
            "  await page.getByRole('link', { name: 'Odd step' }).click();\n"
            "  await page.getByRole('textbox').fill('Secret#123');\n"
            "  await page.getByRole('button', { name: 'Go' }).click();\n});")
    f = [x for x in verify._findings(code) if x.id == "login"]
    assert f and f[0].sev == "Must fix"
    fixed = verify.apply(code, ["login"])
    assert "Secret#123" not in fixed and "name: 'Go'" in fixed and "await login(page)" in fixed


def test_codegen_command_gets_the_url_when_the_state_arrives():
    f = _fn(APP, "refreshState")
    assert "#recCmd" in f and "defaultStart()" in f
    assert 'id="recCmd"' in APP


# ================================================================ reports

def _run_row(rid, err, fail_at, steps, d=""):
    with state.db() as c:
        c.execute("INSERT INTO runs(id,test_id,name,module,author,at,passed,total,result,err,fail_at,steps,dir,ai_fixes,"
                  "ts,run_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (rid, "TC_X", "n", "Sale", "a", "now", 1, len(steps), "Fail", err, fail_at, json.dumps(steps), d, 0,
                   time.time(), ""))


def test_old_runs_show_the_step_named_in_the_error(tmp_path):
    steps = [{"text": f"s{i + 1}", "status": st} for i, st in
             enumerate(["doing", "ok", "ok", "doing", "ok", "ok", "ok", "doing", "ok", "doing", "bad", "skip"])]
    _run_row("R-0022", "Step 1 failed: use_company QA Pharma Distribution", 10, steps, str(tmp_path))
    d = studio_tests.run_detail("R-0022")
    assert d["run"]["failAt"] == 0
    assert d["steps"][0]["status"] == "Fail" and all(s["status"] == "Skip" for s in d["steps"][1:])
    html = studio_tests.report_html("R-0022")
    assert "<td>1</td><td>s1</td><td class='Fail'>" in html and "<td>11</td><td>sleep" not in html
    assert next(r for r in studio_tests.list_runs()["runs"] if r["id"] == "R-0022")["failAt"] == 0
    # a run recorded right is left as it is
    ok = [{"text": "a", "status": "ok"}, {"text": "b", "status": "bad"}, {"text": "c", "status": "ok"}]
    assert studio_tests.fix_fail_step("Step 2 failed: x", 1, ok) == (1, ok)
    assert studio_tests.fix_fail_step("no number", 5, ok) == (5, ok)


def _trace(path: Path, secret: str = ""):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("trace.trace", ('{"type":"action","value":"' + secret + '"}\n') * 2000)
        z.writestr("resources/page@1.jpeg", b"\xff\xd8" + b"x" * 5000)


def test_concurrent_trace_scrubs_do_not_collide(tmp_path):
    for secret in ("", "Qa7-Pass!"):
        p = tmp_path / f"trace{len(secret)}.zip"
        _trace(p, secret)
        errs = []

        def go():
            try:
                executor.scrub_trace(p, ["Qa7-Pass!"])
            except Exception as e:  # noqa: BLE001
                errs.append(e)
        ts = [threading.Thread(target=go) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        assert not errs
        with zipfile.ZipFile(p) as z:
            assert b"Qa7-Pass!" not in z.read("trace.trace")
        assert not list(tmp_path.glob("*.tmp"))


def test_a_clean_trace_is_not_rewritten_and_not_read_again(tmp_path, monkeypatch):
    p = tmp_path / "trace.zip"
    _trace(p)
    before = p.stat().st_mtime_ns
    assert executor.scrub_trace(p, ["Qa7-Pass!"]) is False
    assert p.stat().st_mtime_ns == before
    reads = []
    real = zipfile.ZipFile.read
    monkeypatch.setattr(zipfile.ZipFile, "read", lambda self, n, *a: (reads.append(n), real(self, n, *a))[1])
    assert executor.scrub_trace(p, ["Qa7-Pass!"]) is False and reads == []       # cached: download starts at once
    assert executor.scrub_trace(p, ["Other-Secret"]) is False and reads           # new secrets: checked again


def test_runs_file_serves_only_screenshots(tmp_path):
    (tmp_path / "trace.zip").write_bytes(b"PK")
    (tmp_path / "run.webm").write_bytes(b"v")
    (tmp_path / "X_step01.png").write_bytes(b"\x89PNG")
    _run_row("R-0100", "", -1, [], str(tmp_path))
    assert studio_tests.run_shot_file("R-0100", "X_step01.png").name == "X_step01.png"
    for bad in ("trace.zip", "TRACE.ZIP", "trace.zip.", "trace.zip::$DATA", "run.webm", "X_step01.png::$DATA",
                "../X_step01.png", "X_step01.PNG.zip"):
        with pytest.raises(KeyError):
            studio_tests.run_shot_file("R-0100", bad)


def test_download_error_does_not_show_the_server_path(srv, monkeypatch):   # noqa: F811
    def boom(rid):
        raise PermissionError(r"[WinError 32] used by another process: 'C:\\Users\\x\\testautomation\\trace.zip'")
    monkeypatch.setattr(studio_tests, "trace_bytes", boom)
    op = _login(srv, "qa1@qa.test")
    code, d, _ = _call(op, srv, "/api/download?kind=trace&id=R-0001")
    assert code == 500 and "testautomation" not in d["error"] and "WinError" not in d["error"]


def test_bug_pack_env_names_the_company_the_run_used(store_tmp, tmp_path):
    from ui import store
    store.save(name="Chem", description="", module="sales", case_id="TC_CHEM_X",
               steps=[{"action": "use_company", "value": "QA Pharma Distribution"}, {"action": "sleep", "value": "1"}])
    with state.db() as c:
        c.execute("INSERT INTO runs(id,test_id,name,module,author,at,passed,total,result,err,fail_at,steps,dir,ai_fixes,"
                  "ts,run_by) VALUES('R-0200','TC_CHEM_X','Chem','Sale','a','now',2,2,'Pass','',-1,'[]',?,0,0,'')",
                  (str(tmp_path / "none"),))
    data = studio_tests.bug_pack("R-0200")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        env = z.read("env.txt").decode()
    assert "Company: QA Pharma Distribution" in env


# ================================================================ ops: accounts CLI without a console

def test_cli_reset_checks_the_user_before_asking_a_password(monkeypatch, capsys):
    def never(*a, **k):
        raise AssertionError("asked for a password")
    monkeypatch.setattr(accounts, "_read_password", never)
    assert accounts._cli(["reset", "nobody"]) == 1
    assert "No such user" in capsys.readouterr().out


def test_cli_reads_stdin_when_stdin_is_not_a_console(monkeypatch):
    import sys

    class NotConsole(io.StringIO):
        def isatty(self):
            return True                    # what Windows says for NUL

        def fileno(self):
            raise OSError("no handle")
    monkeypatch.setattr(sys, "stdin", NotConsole(""))
    assert accounts._console_stdin() is False
    assert accounts._read_password("x", False) == ""      # empty -> 'at least 8 characters', no hidden prompt
