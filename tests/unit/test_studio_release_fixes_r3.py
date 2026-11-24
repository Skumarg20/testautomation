"""Release QA round 3: the issues the QA agents found in team-mode Test Studio, one test (or more) each.
No browser and no network: the browser player and the run process are stubs."""
from __future__ import annotations

import io
import json
import threading
import time
import zipfile
from pathlib import Path

import pytest

from ui_studio import executor, memory, recorder, script, state, tests as studio_tests, verify, worker

from tests.unit.test_studio_release_fixes import store_tmp, LINES   # noqa: F401  (fixtures)
from tests.unit.test_studio_release_fixes_r2 import SAMPLE, _fn, _run_row, _trace

APP = (Path(__file__).resolve().parents[2] / "ui_studio" / "app.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "studio_settings.json")
    monkeypatch.setattr(memory, "ALIASES_FILE", tmp_path / "aliases.json")
    monkeypatch.setattr(executor, "_FP_KEY_FILE", tmp_path / "trace_fp.key")
    executor._fp_key_cache.clear()
    executor._clean.clear()
    memory._cache["stamp"] = None
    state.save_settings({"out_dir": str(tmp_path / "specs")})
    yield
    executor._fp_key_cache.clear()
    executor._clean.clear()
    memory._cache["stamp"] = None


# ================================================================ runs

def _job(jid, state_, created, waiting="", title="t"):
    executor.JOBS[jid] = {"id": jid, "kind": "run", "state": state_, "title": title, "created": created,
                          "waiting": waiting, "_owner": {"username": "qa2@qa.test"}, "opts": {"video": True}}


def test_live_runs_put_the_running_run_before_a_newer_queued_one():
    try:
        _job("R-old", "running", 100)
        _job("R-new", "running", 200, waiting="your other run is still using your MargBooks login")
        _job("R-q", "queued", 300)
        runs = executor.live_runs({"username": "qa2@qa.test", "role": "qa"})
        assert [r["id"] for r in runs] == ["R-old", "R-q", "R-new"]
        assert runs[0]["state"] == "running" and all(r["state"] == "queued" for r in runs[1:])
    finally:
        for k in ("R-old", "R-new", "R-q"):
            executor.JOBS.pop(k, None)


def test_resume_run_follows_this_tabs_run_then_a_running_one():
    f = _fn(APP, "resumeRun")
    assert "sessionStorage.getItem('ts.followRun')" in f and "r.state === 'running'" in f
    assert "sessionStorage.setItem('ts.followRun', rid)" in _fn(APP, "followRun")


def test_run_that_never_waited_does_not_keep_the_queued_title(monkeypatch):
    from ui_studio import mode
    monkeypatch.setattr(mode, "MAX_BROWSERS", 4)
    job = {"title": "Queued", "_owner": {"username": "qa2@qa.test", "mb_user": "qa2@x"}, "_stop": threading.Event(),
           "next_title": "TC_SALE_228 · Sale (starting the browser…)"}
    with executor._slot(job, {"steps": []}):
        assert job["title"] == "TC_SALE_228 · Sale (starting the browser…)"
    job2 = {"title": "Queued", "_owner": {}, "_stop": threading.Event()}
    with executor._slot(job2, {"steps": []}):
        assert job2["title"] == "Starting the browser…"


# ================================================================ cases

def test_back_bar_is_dropped_when_the_qa_leaves_by_the_nav_or_goes_back():
    g = _fn(APP, "go")
    assert "v === 'home' || v === 'cases'" in g and "RETURN = null" in g
    i = APP.index("$$('.nav').forEach(b => b.onclick")
    assert "RETURN = null" in APP[i: i + 200]


def test_list_tests_answers_from_the_fresh_list_without_the_lock(store_tmp, monkeypatch):   # noqa: F811
    from ui import store
    store.save(name="A", description="", module="sales", case_id="TC_LST_X", steps=[{"action": "sleep", "value": "1"}])
    studio_tests._LIST.update(key=None, out=None, at=0.0)
    studio_tests.list_tests()
    calls = []
    monkeypatch.setattr(store, "list_all", lambda: (calls.append(1), [])[1])
    t0 = time.time()
    outs = []
    ts = [threading.Thread(target=lambda: outs.append(studio_tests.list_tests())) for _ in range(5)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(10)
    assert len(outs) == 5 and not calls and time.time() - t0 < 2        # no stat of every case file, no queueing
    studio_tests.invalidate_list()
    studio_tests.list_tests()
    assert calls                                                       # a save makes the next call check again


def test_saving_from_write_reloads_the_test_list():
    assert "loadTests()" in _fn(APP, "saveRecorded")


def test_save_invalidates_the_list(store_tmp):   # noqa: F811
    studio_tests._LIST.update(at=time.monotonic() + 999)
    code = script.generate("Smoke", "Sale", "QA Four", LINES)["code"]
    studio_tests.save(code, "Smoke", "Sale", "Low", "d", "QA Four", "written", LINES)
    assert studio_tests._LIST["at"] == 0.0


# ================================================================ write: replay errors

def test_sign_in_is_tried_twice_and_fails_in_plain_words(monkeypatch):
    from framework import auth
    tries = []

    class Ctx:
        def new_page(self):
            class P:
                def close(self):
                    pass
            return P()

    def bad_login(page):
        tries.append(1)
        raise auth.LoginBlocked("'CHEMIST AUTOMATION (AGENT)' Organisation List me nahi mila (ya click kaam nahi kiya).\n"
                                "List me ye 3 naam dikhe:")
    monkeypatch.setattr(auth, "login", bad_login)
    monkeypatch.setattr(executor.settings, "COMPANY", "CHEMIST AUTOMATION (AGENT)", raising=False)
    logs = []
    with pytest.raises(executor.SignInFailed) as e:
        executor._sign_in(Ctx(), logs.append)
    assert len(tries) == 2 and "Trying once more" in logs[0]
    assert "MargBooks login failed" in str(e.value) and "CHEMIST AUTOMATION (AGENT)" in str(e.value)
    assert executor.start_error(e.value) == str(e.value)
    n = []

    def slow_login(page):
        n.append(1)
        if len(n) == 1:
            raise auth.LoginBlocked("Organisation List me nahi mila")
        return "bp"
    monkeypatch.setattr(auth, "login", slow_login)
    assert executor._sign_in(Ctx(), logs.append) == "bp" and len(n) == 2   # the second try opened the company


def test_worker_error_reaches_the_replay_panel_without_a_traceback(monkeypatch):
    class Proc:
        returncode = 1

        def __init__(self, lines):
            self.stdout = iter(lines)

        def wait(self, timeout=None):
            return 1
    lines = ["Traceback (most recent call last):\n", '  File "x.py", line 1, in <module>\n',
             "ui_studio.executor.SignInFailed: MargBooks login failed: the company X did not open\n",
             worker.MARK + json.dumps({"ev": "error", "kind": "SignInFailed", "m": "MargBooks login failed: the company X did not open"}) + "\n"]
    errs, logs = [], []
    assert executor._read_worker(Proc(lines), worker.MARK, None, logs.append, errs) is None
    assert errs and errs[0]["kind"] == "SignInFailed"
    job = {"log": "Signing in...\n" + "".join(lines[:3]) + "Sign-in try 1 failed: x\n"}
    tail = executor.log_tail(job)
    assert "Traceback" not in tail and "File " not in tail and "Signing in..." in tail and "Sign-in try 1" in tail


def test_replay_failure_shows_the_reason_not_could_not_start(monkeypatch):
    jid = "rTEST1"
    code = script.generate("Smoke", "Sale", "QA Four", LINES)["code"]
    executor.JOBS[jid] = {"id": jid, "kind": "replay", "code": code, "name": "n", "dir": "x", "attempt": 0,
                          "aiFixes": 0, "max": 2, "tokens": {"local": 0}, "_owner": {}, "_stop": threading.Event(),
                          "log": ""}

    def play(*a, **k):
        raise executor.SignInFailed("MargBooks login failed: the company X did not open from the Organisation List.")
    try:
        executor._replay_thread(jid, play)
        j = executor.JOBS[jid]
        assert j["state"] == "failed" and j["err"]["plain"].startswith("MargBooks login failed")
        assert "Traceback" not in j["err"]["err"] and "executor.py" not in j["err"]["err"]
        assert "Traceback" in j["log"]                                   # still in the log for developers
    finally:
        executor.JOBS.pop(jid, None)


def test_worker_reports_an_exception_as_an_error_event(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO('{"cases": [], "opts": {}}'))

    def boom(*a, **k):
        raise executor.SignInFailed("MargBooks login failed: nope")
    monkeypatch.setattr(executor, "_play", boom)
    assert worker.main() == 1
    out = capsys.readouterr().out
    ev = [json.loads(ln[len(worker.MARK):]) for ln in out.splitlines() if ln.startswith(worker.MARK)]
    assert ev[-1] == {"ev": "error", "kind": "SignInFailed", "m": "MargBooks login failed: nope"}


def test_org_pick_waits_for_a_slow_company_after_the_click(monkeypatch):
    from framework import auth
    calls = []

    def ready(page, ms=20000):
        calls.append(ms)
        return len(calls) > 1                 # not within the short wait, but within the long one

    class BP:
        page = object()

        def page_has_text(self, t):
            return False                      # the Organisation List is gone: the company is opening
    monkeypatch.setattr(auth, "app_ready", ready)
    assert auth._org_opened(BP(), 12000) is True and calls == [12000, 60000]
    calls.clear()

    class BPList(BP):
        def page_has_text(self, t):
            return True                       # still on the list: the click did nothing, try the next way
    assert auth._org_opened(BPList(), 12000) is False and calls == [12000]


# ================================================================ record: password after many unknown steps

FOUR = SAMPLE.replace("  await page.getByRole('link', { name: 'Login with password' }).click();\n",
                      "".join(f"  await page.getByRole('link', {{ name: '{c}' }}).click();\n" for c in "abcd"))


def test_password_after_four_unknown_login_steps_is_removed():
    assert "name: 'd'" in FOUR
    p = recorder.paste(FOUR)["code"]
    assert "Placeholder#Pass1" not in p and "await login(page)" in p
    assert "Placeholder#Pass1" not in studio_tests.redact_code(FOUR, [])
    assert "utillity-menu" in p and "Data Backup" in p


def test_many_unknown_steps_without_a_password_stay_in_the_test():
    code = SAMPLE.replace("  await page.getByRole('link', { name: 'Login with password' }).click();\n", "")
    code = code.replace("  await page.goto('https://books6.margbooks.com/mb/utillity-menu');",
                        "".join(f"  await page.getByRole('link', {{ name: 'M{k}' }}).click();\n" for k in range(5))
                        + "  await page.getByRole('button', { name: 'Continue' }).click();")
    ls = code.split("\n")
    kept = [ls[i] for i in range(len(ls)) if i not in script.login_block(code)]
    assert all(any(f"name: 'M{k}'" in x for x in kept) for k in range(5))


def test_verify_flags_a_password_after_four_clicks_after_login_page():
    code = ("import { test } from '@playwright/test';\nimport { login } from '../helpers/mb';\n"
            "test('x', async ({ page }) => {\n  await login(page);\n"
            + "".join(f"  await page.getByRole('link', {{ name: '{c}' }}).click();\n" for c in "abcd")
            + "  await page.getByRole('textbox').fill('Secret#123');\n"
              "  await page.getByRole('button', { name: 'Go' }).click();\n});")
    f = [x for x in verify._findings(code) if x.id == "login"]
    assert f and f[0].sev == "Must fix"
    assert "Secret#123" not in verify.apply(code, ["login"])
    # a search typed after a real page step is a test step, not a password
    code2 = code.replace("  await page.getByRole('link', { name: 'b' }).click();\n",
                         "  await page.getByRole('textbox', { name: 'Search' }).fill('Paracetamol');\n")
    assert not [x for x in verify._findings(code2) if x.id == "login"]


# ================================================================ reports

def test_bug_pack_steps_match_the_drawer_and_have_no_doing(tmp_path):
    steps = [{"text": f"s{i + 1}", "status": st} for i, st in
             enumerate(["doing", "ok", "ok", "doing", "ok", "ok", "ok", "doing", "ok", "doing", "bad", "skip"])]
    _run_row("R-0022", "Step 1 failed: use_company QA Pharma Distribution", 10, steps, str(tmp_path))
    with zipfile.ZipFile(io.BytesIO(studio_tests.bug_pack("R-0022"))) as z:
        txt = z.read("steps.txt").decode()
    assert "1. [FAIL] s1" in txt and "11. [skip] s11" in txt and "[doing]" not in txt and "[bad]" not in txt
    # a run whose failing step was still "doing" (R-0026): that step is the failed one
    st2 = [{"text": "a", "status": "ok"}, {"text": "b", "status": "doing"}, {"text": "c", "status": "todo"}]
    _run_row("R-0026", "Alert Item is Banned", 1, st2, str(tmp_path))
    d = studio_tests.run_detail("R-0026")
    assert [s["status"] for s in d["steps"]] == ["Pass", "Fail", "Skip"]
    with zipfile.ZipFile(io.BytesIO(studio_tests.bug_pack("R-0026"))) as z:
        txt = z.read("steps.txt").decode()
    assert "2. [FAIL] b" in txt and "3. [skip] c" in txt


def test_new_runs_store_no_doing_status(tmp_path):
    job = {"dir": str(tmp_path), "_owner": {"username": "qa"}}
    c = {"display_id": "TC_X", "name": "n", "module": "Sale", "author": "a", "id": "TC_X"}
    steps = [{"text": "a", "status": "ok"}, {"text": "b", "status": "doing"}, {"text": "c", "status": "todo"}]
    executor._save_run(job, c, {"outcome": "failed", "error": "x", "failed_step": 1}, steps, 1)
    with state.db() as con:
        r = con.execute("SELECT steps FROM runs").fetchone()
    assert [s["status"] for s in json.loads(r["steps"])] == ["ok", "bad", "skip"]


def test_bug_pack_stores_video_and_trace_without_compressing_them_again(tmp_path):
    (tmp_path / "run.webm").write_bytes(b"\x1aE" + bytes(range(256)) * 400)
    _trace(tmp_path / "trace.zip")
    (tmp_path / "X_step01.png").write_bytes(b"\x89PNG" + b"0" * 100)
    _run_row("R-0300", "", -1, [], str(tmp_path))
    with zipfile.ZipFile(io.BytesIO(studio_tests.bug_pack("R-0300"))) as z:
        kinds = {i.filename: i.compress_type for i in z.infolist()}
    assert kinds["run.webm"] == zipfile.ZIP_STORED and kinds["trace.zip"] == zipfile.ZIP_STORED
    assert kinds["screenshots/X_step01.png"] == zipfile.ZIP_STORED and kinds["steps.txt"] == zipfile.ZIP_DEFLATED


# ================================================================ ops: clean trace survives a restart

def test_clean_marker_survives_a_restart_and_the_run_process(tmp_path, monkeypatch):
    p = tmp_path / "trace.zip"
    _trace(p)
    # the run process scrubs at save time with its own password
    assert executor.scrub_trace(p, ["Qa2-Pass!"]) is False
    assert (tmp_path / "trace.zip.clean").exists()
    raw = (tmp_path / "trace.zip.clean").read_text(encoding="utf-8")
    assert "Qa2-Pass!" not in raw
    # server restart: in-memory cache gone, a new per-process key
    executor._clean.clear()
    monkeypatch.setattr(executor, "_FP_KEY", b"another process")
    reads = []
    real = zipfile.ZipFile.read
    monkeypatch.setattr(zipfile.ZipFile, "read", lambda self, n, *a: (reads.append(n), real(self, n, *a))[1])
    subs = []
    real_sub = executor.scrub_bytes
    monkeypatch.setattr(executor, "scrub_bytes", lambda d, s: (subs.append(1), real_sub(d, s))[1])
    assert executor.scrub_trace(p, ["Qa2-Pass!"]) is False and reads == [] and subs == []    # instant
    # the download also checks every other QA's password: a quick search, no full regex scrub
    assert executor.scrub_trace(p, ["Qa2-Pass!", "Qa3-Pass!"]) is False and reads and subs == []
    executor._clean.clear()
    reads.clear()
    assert executor.scrub_trace(p, ["Qa3-Pass!", "Qa2-Pass!"]) is False and reads == []       # now remembered


def test_clean_marker_does_not_hide_a_password_in_a_changed_or_other_trace(tmp_path):
    p = tmp_path / "trace.zip"
    _trace(p)
    executor.scrub_trace(p, ["Qa2-Pass!"])
    _trace(p, "Qa3-Pass!")                    # the file changed after it was marked
    executor._clean.clear()
    assert executor.scrub_trace(p, ["Qa2-Pass!", "Qa3-Pass!"]) is True
    with zipfile.ZipFile(p) as z:
        assert b"Qa3-Pass!" not in z.read("trace.trace")
    # marked clean for Qa2 only, but holds Qa4's password: the quick search finds it and the full scrub runs
    q = tmp_path / "t2.zip"
    _trace(q, "Qa4-Pass!")
    executor.scrub_trace(q, ["Qa2-Pass!"])
    executor._clean.clear()
    assert executor.scrub_trace(q, ["Qa2-Pass!", "Qa4-Pass!"]) is True
    with zipfile.ZipFile(q) as z:
        assert b"Qa4-Pass!" not in z.read("trace.trace")
