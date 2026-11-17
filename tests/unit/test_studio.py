"""
Test Studio (ui_studio/): step grammar, verify rules, script round trip, AI guard rails, replay loop, HTTP layer.
No browser and no network: the browser part of the executor is replaced by a stub, and the AI by a fake.
Every test works on temp copies of the Studio database, settings and taught words.
"""
import json
import threading
import urllib.request

import pytest

from ui_studio import executor, grammar, memory, recorder, script, state, tests as studio_tests, verify

LINES = [
    "Log in", "create sale bill", 'enter date "16-11-2026"', 'search party "Ajay"', 'select party "Ajay"',
    'select item "dolo" with qty "2", rate "100", discount "10"', "save bill", 'verify "Bill saved"',
    "wait 2 seconds",
]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "studio_settings.json")
    monkeypatch.setattr(memory, "ALIASES_FILE", tmp_path / "aliases.json")
    memory._cache["stamp"] = None
    state.save_settings({"out_dir": str(tmp_path / "specs")})
    yield
    memory._cache["stamp"] = None


@pytest.fixture
def fake_ai(monkeypatch):
    """Replace the provider. answers: dict of feature -> reply. Counts real calls."""
    from framework import ai
    calls = []
    answers = {}
    monkeypatch.setattr(ai, "available", lambda: {"active": "gemini", "model": "fake"})

    def ask_json(system, user, max_tokens=0):
        calls.append(user)
        return answers.get("next", {"line": ""})
    monkeypatch.setattr(ai, "ask_json", ask_json)
    return type("F", (), {"calls": calls, "answers": answers})


# ----------------------------------------------------------------- memory

def test_memory_has_real_stable_locators():
    sb = memory.build()["screens"]["Sale Bill"]
    party = next(f for f in sb["fields"] if f["name"] == "Party Name")
    assert party["sel"] == '[formcontrolname="ledgerName"]' and party["stab"] >= 94
    date = next(f for f in sb["fields"] if f["name"] == "Bill Date")
    assert date["sel"].startswith('[id^="txtbillDate"')          # tab number stripped, not a fixed id
    assert date["stab"] < party["stab"]                          # fcn beats id with a number
    assert {"Product", "Qty", "Rate", "Disc 1.%"} <= {f["name"] for f in sb["fields"]}


def test_memory_skips_data_rows_and_danger():
    names = {f["name"] for s in memory.build()["screens"].values() for f in s["fields"]}
    assert not any(n.strip().isdigit() for n in names)


def test_taught_word_applies_for_everyone():
    r = grammar.check(["create sale bill", 'enter discout "5"'])
    assert r["results"][1]["status"] == "bad"
    memory.teach("discout", "Sale Bill", "Disc 1.%")
    r = grammar.check(["create sale bill", 'enter discout "5"'])
    assert r["results"][1]["status"] == "ok" and r["results"][1]["learned"] is True
    assert memory.rows(q="discout")["rows"][0]["taught"] == ["discout"]


# ---------------------------------------------------------------- grammar

def test_every_example_line_maps():
    r = grammar.check(LINES + ["create 500 sale bills with 50 items each, random party and random items"])
    assert r["bad"] == 0, [x for x in r["results"] if x["status"] == "bad"]
    items = r["results"][5]
    assert [e["field"]["name"] for e in items["extras"]] == ["Qty", "Rate", "Disc 1.%"]
    assert items["field"]["sel"].startswith('[id^="txt-itemLinkID')


@pytest.mark.parametrize("line", ["Open Sale Bill", "Enter 5 in Disc 1.%", "Set Rate to 50", "Click Save", "# a note"])
def test_mockup_forms(line):
    r = grammar.check(["Open Sale Bill"] + ([line] if line != "Open Sale Bill" else []))
    assert r["results"][-1]["status"] in ("ok", "note")


def test_values_keep_their_case_and_quotes():
    r = grammar.check(["create sale bill", 'select party "AjAy Sharma"'])["results"][1]
    assert r["value"] == "AjAy Sharma"


def test_typo_is_red_with_free_suggestion():
    r = grammar.check(["create sale bill", 'select item "dolo" with qty "2", disocunt "10"'])["results"][1]
    assert r["status"] == "bad" and r["term"] == "disocunt" and "Disc 1.%" in r["fixes"]


def test_unknown_screen_and_field_on_wrong_screen():
    r = grammar.check(["open purshase bill"])["results"][0]
    assert r["status"] == "bad" and "Open Purchase Bill" in r["sugg"]
    r = grammar.check(["Open Sale Bill List", 'enter rate "5"'])["results"][1]
    assert r["status"] == "bad"


def test_field_line_before_any_screen_is_red():
    r = grammar.check(['enter rate "5"'])["results"][0]
    assert r["status"] == "bad" and "Open a screen first" in r["note"]


def test_bulk_limit_and_gibberish():
    assert grammar.check(["create 6000 sale bills"])["results"][0]["status"] == "bad"
    r = grammar.check(["asdf qwer zxcv"])["results"][0]
    assert r["status"] == "bad" and r["ai"] is True


def test_yaml_steps_for_the_project_runner():
    steps = grammar.to_steps(LINES)
    acts = [s["action"] for s in steps]
    assert acts == ["note", "open_screen", "fill", "set_party", "add_item", "save_form", "assert_text", "sleep"]
    assert steps[4]["value"] == "dolo | 2 | 100 | 10"
    assert steps[1]["target"] == "sale_bill"
    with pytest.raises(ValueError):
        grammar.to_steps(["create sale bill", 'enter nonsense "5"'])


# ------------------------------------------------------------- script

def test_generate_refuses_red_lines():
    with pytest.raises(ValueError):
        script.generate("x", "Sale", "Ajay", ["create sale bill", 'enter nonsense "5"'])


def test_script_round_trips_to_the_same_steps():
    code = script.generate("Sale bill with discount", "Sale", "Ajay Rai", LINES)["code"]
    assert "await setParty(page, 'Ajay');" in code and "await addItem(page, {" in code
    conv = script.to_steps(code)
    assert conv["unknown"] == []
    clean = [{k: v for k, v in s.items() if k not in ("note", "_line")} for s in conv["steps"]]
    want = [{k: v for k, v in s.items() if k != "note"} for s in grammar.to_steps(LINES)]
    assert clean == want                      # the search+select pair became ONE set_party step


def test_codegen_lines_convert_and_unreadable_ones_are_reported_not_guessed():
    code = ("import { test } from '@playwright/test';\ntest('x', async ({ page }) => {\n"
            "  await page.getByPlaceholder('Password').fill('secret');\n"
            "  await page.getByRole('button', { name: 'Save' }).click();\n"
            "  await page.mouse.wheel(0, 100);\n});\n")
    conv = script.to_steps(code)
    assert [s["action"] for s in conv["steps"]] == ["click"]
    assert len(conv["unknown"]) == 2 and "login" in conv["unknown"][0]["why"].lower()


def test_recorder_json_is_importable_shape():
    steps = grammar.to_steps(LINES)
    out = json.loads(script.recorder_json("TC-1 x", "https://books5.margbooks.com", steps))
    types = [s["type"] for s in out["steps"]]
    assert types[:2] == ["setViewport", "navigate"] and "change" in types and "waitForElement" in types
    assert "password" not in json.dumps(out).lower()


# ------------------------------------------------------------- verify

BAD = """import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('https://books5.margbooks.com/login');
  await page.getByPlaceholder('User ID').fill('tester@marg.in');
  await page.getByPlaceholder('Password').fill(process.env.MB_PASS!);
  await page.getByRole('button', { name: 'Login' }).click();
  await page.waitForTimeout(3000);
  await page.locator('#mat-input-7').fill('10');
  await page.locator('[formcontrolname="ledgerName"]').fill('Cash');
  await page.locator('[formcontrolname="ledgerName"]').fill('Cash');
  await page.getByRole('button', { name: 'F10 / End Save' }).click();
});
"""
GOOD = script_ok = None


def ids(code):
    return {f["id"].split("-")[0] for f in verify.run(code)["findings"]}


def test_each_rule_fires_on_a_bad_script(monkeypatch):
    monkeypatch.setattr(state, "ai_json", lambda *a, **k: (_ for _ in ()).throw(state.AIBlocked("off")))
    got = ids(BAD)
    assert {"login", "wait", "pos", "dup", "name", "assert"} <= got


def test_clean_script_has_no_findings():
    code = script.generate("Sale bill", "Sale", "Ajay", ["Log in", "create sale bill", 'select party "Ajay"',
                                                         "save bill", 'verify "Bill saved"'])["code"]
    assert [f["id"] for f in verify.run(code)["findings"]] == []


def test_wait_rule_spares_a_wait_the_tester_asked_for():
    code = script.generate("w", "Sale", "A", ["Log in", "wait 2 seconds"])["code"]
    assert "wait" not in ids(code)


def test_apply_login_wait_dup_and_import(monkeypatch):
    monkeypatch.setattr(state, "ai_json", lambda *a, **k: (_ for _ in ()).throw(state.AIBlocked("off")))
    out = verify.apply(BAD, ["login", "wait", "dup"])
    assert "await login(page);" in out and "Password" not in out and "waitForTimeout" not in out
    assert "import { login } from '../helpers/mb';" in out
    assert out.count("fill('Cash')") == 1


def test_position_rule_uses_memory_only_when_it_knows_the_field(monkeypatch):
    monkeypatch.setattr(state, "ai_json", lambda *a, **k: (_ for _ in ()).throw(state.AIBlocked("off")))
    f = next(x for x in verify.run(BAD)["findings"] if x["id"].startswith("pos"))
    assert f["manual"] is True                # no screen/comment to go on and AI off: honest "edit by hand"
    code = ("test('x', async ({ page }) => {\n  await openScreen(page, 'sale_bill');\n"
            "  // enter qty \"5\"\n  await page.locator('#mat-input-7').fill('5');\n});\n")
    f = next(x for x in verify.run(code)["findings"] if x["id"].startswith("pos"))
    assert f["manual"] is False and 'txt-unitToEnteredValue' in f["neu"][0]
    assert 'txt-unitToEnteredValue' in verify.apply(code, [f["id"]])


def test_assert_rule_ai_answer_is_cleaned_and_logged(fake_ai):
    fake_ai.answers["next"] = {"text": "Bill saved successfully"}
    code = script.generate("s", "Sale", "A", ["Log in", "create sale bill", "save bill"])["code"]
    f = next(x for x in verify.run(code)["findings"] if x["id"] == "assert")
    assert f["src"] == "AI" and f["tokens"] > 0 and "Bill saved successfully" in f["neu"][-1]
    n = len(fake_ai.calls)
    verify.run(code)                          # same snippet again: cache, 0 tokens
    assert len(fake_ai.calls) == n


# ----------------------------------------------------------------- AI

def test_ai_blocked_by_mode_and_limit_but_local_work_continues(fake_ai):
    state.save_settings({"ai_mode": "never"})
    with pytest.raises(state.AIBlocked):
        state.ai_json("f", "s", "u")
    state.save_settings({"ai_mode": "local_first", "token_limit": 1})
    state.ai_json("f", "s", "first")           # uses tokens
    with pytest.raises(state.AIBlocked) as e:
        state.ai_json("f", "s", "second")
    assert "limit" in str(e.value).lower()
    assert grammar.check(LINES)["bad"] == 0    # local checks unaffected


def test_token_log_per_feature_and_month(fake_ai):
    state.ai_json("replay.fix", "sys", "x" * 400, case_id="TC-9")
    rep = state.tokens_report()
    assert rep["by_feature"]["replay.fix"]["calls"] == 1 and rep["month"] >= 100
    assert state.tokens_for_case("TC-9") == rep["month"]


def test_ai_line_suggestion_rejected_when_not_in_memory(fake_ai):
    from ui_studio import server
    fake_ai.answers["next"] = {"line": "Click Teleport"}
    r = server.ai_suggest("do the thing", "Sale Bill")
    assert r["ok"] is False and "does not match app memory" in r["msg"]
    fake_ai.answers["next"] = {"line": "Set Rate to 50"}
    r = server.ai_suggest("rate is fifty", "Sale Bill")
    assert r["ok"] is True and r["rewrite"] == "Set Rate to 50"


# --------------------------------------------------------------- replay

def _job(code, fix_attempts=3):
    state.save_settings({"fix_attempts": fix_attempts})
    jid = "rtest"
    executor.JOBS[jid] = {"id": jid, "kind": "replay", "state": "queued", "attempt": 0, "max": fix_attempts, "aiFixes": 0,
                          "steps": [], "err": None, "code": code, "fixedLines": [], "giveUp": False,
                          "tokens": {"local": 0, "ai": 0}, "log": "", "name": "t", "module": "Sale", "author": "A",
                          "case_id": "", "fixText": "", "dir": "x"}
    return jid


CODE = ("test('t', async ({ page }) => {\n  await login(page);\n"
        "  await page.locator('#mat-input-7').fill('10');\n  await saveForm(page);\n});\n")


def _stub(outcomes):
    seq = iter(outcomes)

    def play(cases, opts, on_step, on_log, stop=None):
        o = next(seq)
        for i, _ in enumerate(cases[0]["steps"]):
            on_step(0, i, "bad" if (o.get("failed_step") == i) else "ok", 0.1, None)
        return [{"outcome": o["outcome"], "error": o.get("error"), "failed_step": o.get("failed_step", -1),
                 "seconds": 1, "shots": []}]
    return play


def test_replay_fails_then_ai_fixes_then_passes(fake_ai):
    fake_ai.answers["next"] = {"line": "  await page.locator('[id^=\"txt-unitToEnteredValue-\"]').fill('10');", "why": "stable id"}
    jid = _job(CODE)
    err = "Step 2 failed: x\nTimeoutError: locator('#mat-input-7') not found"
    executor._replay_thread(jid, play=_stub([{"outcome": "failed", "error": err, "failed_step": 1},
                                             {"outcome": "passed"}]))
    j = executor.replay_status(jid)
    assert j["state"] == "passed" and j["aiFixes"] == 1 and j["attempt"] == 2
    assert "txt-unitToEnteredValue" in j["code"] and "mat-input-7" not in j["code"]
    assert j["fixedLines"] and j["tokens"]["ai"] > 0


def test_replay_rejects_an_ai_fix_that_invents_a_locator(fake_ai):
    fake_ai.answers["next"] = {"line": "  await page.locator('#made-up').fill('10');", "why": "x"}
    jid = _job(CODE)
    executor._replay_thread(jid, play=_stub([{"outcome": "failed", "error": "Timeout", "failed_step": 1}]))
    j = executor.replay_status(jid)
    assert j["state"] == "failed" and j["giveUp"] and "not in app memory" in j["err"]["fixText"]
    assert "made-up" not in j["code"]


def test_disabled_field_is_reported_as_a_setting_not_fixed_by_ai(fake_ai):
    jid = _job(CODE)
    executor._replay_thread(jid, play=_stub([{"outcome": "failed", "error": "element is disabled", "failed_step": 1}]))
    j = executor.replay_status(jid)
    assert j["state"] == "failed" and j["giveUp"] and "setting" in j["err"]["plain"].lower()
    assert fake_ai.calls == []                # no tokens spent


def test_zero_attempts_means_ask_me(fake_ai):
    jid = _job(CODE, fix_attempts=0)
    executor._replay_thread(jid, play=_stub([{"outcome": "failed", "error": "Timeout", "failed_step": 1}]))
    assert executor.replay_status(jid)["giveUp"] and fake_ai.calls == []


def test_unreplayable_lines_stop_before_any_browser_opens():
    jid = _job("test('t', async ({ page }) => {\n  await page.mouse.wheel(0, 9);\n});\n")
    executor._replay_thread(jid, play=lambda *a, **k: pytest.fail("browser must not start"))
    assert executor.replay_status(jid)["state"] == "failed"


def test_diagnose_wording():
    assert "More than one" in executor.diagnose("strict mode violation: x resolved to 2 elements")["plain"]
    assert "covered" in executor.diagnose("element is covered by <div class='batch'>")["plain"]


# ---------------------------------------------------------------- record

def test_codegen_command_is_an_argv_list_and_validated():
    from pathlib import Path
    argv = recorder.build_command("https://books5.margbooks.com/login", Path("out.spec.ts"), False)
    assert argv[0].lower().endswith(("python.exe", "python")) and "codegen" in argv
    assert argv[argv.index("codegen") + 1] == "https://books5.margbooks.com/login"
    assert argv[-2:] == ["-o", "out.spec.ts"]
    with pytest.raises(ValueError):
        recorder.build_command("javascript:alert(1)", Path("o"), False)
    state.save_settings({"codegen_cmd": "cmd /c calc codegen"})
    with pytest.raises(ValueError):
        recorder.build_command("https://x.com", Path("o"), False)


def test_reuse_login_without_a_saved_session_says_so(monkeypatch, tmp_path):
    from config.settings import settings
    monkeypatch.setattr(settings, "STORAGE_STATE", tmp_path / "none.json", raising=False)
    with pytest.raises(ValueError, match="No saved login"):
        recorder.build_command("https://x.com", tmp_path / "o", True)
    assert "playwright install" in recorder.friendly("Executable doesn't exist at some path")


def test_recorded_password_never_stays_in_the_script():
    code = "  await page.getByPlaceholder('Password').fill('Demo@1234');\n  await page.getByPlaceholder('User ID').fill('a@b.c');"
    out = recorder.redact(code)
    assert "Demo@1234" not in out and "MB_PASS" in out and "a@b.c" in out
    assert recorder.describe("await page.getByPlaceholder('Password').fill('x');") == "Typed password"


# --------------------------------------------------- save, runs, downloads

@pytest.fixture
def saved(tmp_path, monkeypatch):
    from ui import store
    monkeypatch.setattr(store, "SAVED", tmp_path / "saved")
    (tmp_path / "saved").mkdir()
    monkeypatch.setattr(store, "list_all", lambda: __import__("framework.case_loader", fromlist=["x"]).load_all(tmp_path / "saved"))
    code = script.generate("Sale bill with discount", "Sale", "Ajay Rai", LINES)["code"]
    return studio_tests.save(code, "Sale bill with discount", "Sale", "High", "checks discount", "Ajay Rai", "written", LINES)


def test_save_writes_yaml_and_spec_with_header(saved):
    assert saved["id"] == "TC-001"
    import yaml
    case = yaml.safe_load(open(saved["yaml"], encoding="utf-8"))[0]
    assert case["id"] == "TC_001" and case["module"] == "sales" and case["destructive"] is True
    assert "Created by Ajay Rai" in case["preconditions"][0]
    head = open(saved["spec"], encoding="utf-8").read().split("\n")[:4]
    assert head[0].startswith("// TC-001") and "Written by: Ajay Rai" in head[1] and "Description: checks discount" in head[2]
    assert saved["spec"].endswith("tc-001-sale-bill-with-discount.spec.ts")
    t = next(x for x in studio_tests.list_tests() if x["id"] == "TC-001")
    assert t["author"] == "Ajay Rai" and t["type"] == "written" and t["lines"] == LINES


def test_save_requires_module_name_and_author():
    for kw in ({"module": ""}, {"name": ""}, {"author": ""}):
        args = {"module": "Sale", "name": "n", "author": "a"} | kw
        with pytest.raises(ValueError):
            studio_tests.save("x", args["name"], args["module"], "", "", args["author"], "record")


def test_bug_pack_has_everything_and_no_password(saved, tmp_path, monkeypatch):
    import io, zipfile
    from ui import envs
    d = tmp_path / "run"
    d.mkdir()
    (d / "run.webm").write_bytes(b"v")
    (d / "trace.zip").write_bytes(b"t")
    (d / "TC_001_step01.png").write_bytes(b"p")
    steps = [{"text": "Log in", "status": "ok"}, {"text": "Save", "status": "bad"}]
    with state.db() as c:
        c.execute("INSERT INTO runs VALUES('R-0001','TC-001','n','Sale','Ajay Rai','now',1,2,'Fail','boom',1,?,?,0,1)",
                  (json.dumps(steps), str(d)))
    monkeypatch.setattr(envs, "apply_active", lambda: {"app_url": "https://x", "company": "C", "password": "TopSecret1"})
    z = zipfile.ZipFile(io.BytesIO(studio_tests.bug_pack("R-0001")))
    names = set(z.namelist())
    assert {"run.webm", "trace.zip", "test.spec.ts", "recorder.json", "steps.txt", "env.txt",
            "screenshots/TC_001_step01.png"} <= names
    assert all(b"TopSecret1" not in z.read(n) for n in names)
    assert b"Written by: Ajay Rai" in z.read("steps.txt")
    det = studio_tests.run_detail("R-0001")
    assert det["files"]["video"] and det["files"]["trace"] and det["steps"][1]["status"] == "Fail"
    with pytest.raises(KeyError):
        studio_tests.run_file("R-0001", "../../etc/passwd")


# ------------------------------------------------------------- HTTP

@pytest.fixture
def http():
    from http.server import ThreadingHTTPServer
    from ui_studio import server
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def call(path, body=None):
        req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    yield call
    srv.shutdown()


def test_api_write_flow_over_http(http):
    s, r = http("/api/write/check", {"lines": LINES})
    assert s == 200 and r["bad"] == 0 and len(r["results"]) == len(LINES)
    s, r = http("/api/write/generate", {"name": "n", "module": "Sale", "author": "A", "lines": LINES})
    assert s == 200 and r["actions"] >= 6
    s, v = http("/api/verify", {"code": r["code"], "src": "written"})
    assert s == 200 and "findings" in v and v["tokens"]["ai"] == 0
    s, e = http("/api/write/generate", {"name": "n", "module": "Sale", "author": "A", "lines": ['enter junk "1"']})
    assert s == 400 and "red lines" in e["error"]


def test_api_state_settings_never_leak_the_password(http, monkeypatch):
    from ui import envs
    monkeypatch.setattr(envs, "apply_active", lambda: {"name": "d", "app_url": "https://x", "login_url": "https://x/login",
                                                       "user": "u", "password": "TopSecret1", "company": "C"})
    s, st = http("/api/state")
    assert s == 200 and set(st) >= {"env", "modules", "users", "ai", "memory", "kpis"}
    s, se = http("/api/settings")
    assert s == 200 and se["has_password"] is True and "TopSecret1" not in json.dumps(se)
    assert {o["value"] for o in se["trade_options"]} >= {"auto", "Pharma Agent"}


def test_api_errors_are_plain_json(http):
    assert http("/api/nope")[0] == 404
    s, e = http("/api/replay/status?job=missing")
    assert s == 404 and "error" in e
    s, e = http("/api/save", {"code": "x", "name": "", "module": "", "author": ""})
    assert s == 400 and "required" in e["error"]


def test_api_download_unknown_file_is_404_not_a_traceback(http):
    s, e = http("/api/download?kind=trace&id=R-9999")
    assert s == 404 and "error" in e
