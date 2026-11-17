"""
Replay, AI auto-fix and Run for Test Studio.

The browser part is ONE function (_play). It uses the project's own login, safety
guards, netguard and StepRunner, exactly like ui/runner.py, and adds: per-step status,
per-step screenshots, video and trace. Everything around it (job state, fix loop,
database, reports) is plain Python and does not need a browser.
"""
from __future__ import annotations

import re
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

from config.settings import ROOT, settings
from ui_studio import memory, script, state, verify

JOBS: dict[str, dict] = {}
_browser_lock = threading.Lock()      # one browser at a time
RUNS_DIR = ROOT / "artifacts" / "studio"


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6]}"


def _log(job: dict, text: str):
    job["log"] = (job.get("log", "") + text + "\n")[-6000:]


# ================================================================== browser

def ffmpeg_ready() -> bool:
    """Video needs the ffmpeg that `python -m playwright install` downloads. Without it new_page() crashes."""
    import os
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright"),
             os.path.expanduser("~/.cache/ms-playwright"), os.path.expanduser("~/Library/Caches/ms-playwright")]
    return any(r and Path(r).is_dir() and any(Path(r).glob("ffmpeg-*")) for r in roots)


def _play(cases: list[dict], opts: dict, on_step, on_log, stop: threading.Event | None = None) -> list[dict]:
    """
    Run cases in one browser. cases = [{"id","name","steps":[...],"destructive":bool}].
    on_step(case_index, step_index, status, secs, shot_path|None) is called live.
    Returns one result per case: {"outcome","error","failed_step","seconds","video","trace","shots":[]}.
    """
    from playwright.sync_api import sync_playwright
    from framework import safety, netguard
    from framework.auth import login, app_ready
    from framework.browser import launch
    from framework.step_runner import StepRunner, RunContext, StepFailed, TradeMismatch
    from framework.screens_check import ensure_neutral
    from framework.control_room import FeatureOff, SettingLocked
    from ui import envs

    envs.apply_active()
    if opts.get("video", True) and not ffmpeg_ready():
        opts = dict(opts, video=False)
        on_log("Video skipped: ffmpeg is not installed. Run: python -m playwright install chromium")
    out_dir = Path(opts["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    settings.init_run(f"Studio {opts.get('label', '')}")
    safety.CLICK_LOG.clear()
    netguard.BLOCKED.clear()
    results: list[dict] = []
    with sync_playwright() as pw:
        browser, ctx = launch(pw, record_video=bool(opts.get("video", True)))
        try:
            if opts.get("trace", True):
                ctx.tracing.start(screenshots=True, snapshots=True, sources=False)
            on_log("Signing in...")
            bp = login(ctx.new_page())
            on_log("Signed in")
            for ci, case in enumerate(cases):
                if stop is not None and stop.is_set():
                    break
                res = {"id": case["id"], "outcome": "passed", "error": None, "failed_step": -1,
                       "seconds": 0.0, "shots": []}
                results.append(res)
                steps = case["steps"]
                if case.get("destructive") and not settings.ALLOW_DESTRUCTIVE:
                    res.update(outcome="skipped", error="This test writes data. Turn on “Allow writes” in Settings.")
                    for i in range(len(steps)):
                        on_step(ci, i, "skip", 0, None)
                    continue
                if not app_ready(bp.page, 4000):
                    on_log("Session ended, signing in again")
                    bp = login(ctx.new_page())
                ensure_neutral(bp)
                runner = StepRunner(bp, RunContext())
                orig = runner._dispatch
                state_i = {"i": -1, "t0": 0.0}

                def dispatch(action, target, value, step, _ci=ci, _orig=orig, _st=state_i, _res=res, _bp=bp):
                    _st["i"] += 1
                    i = _st["i"]
                    on_step(_ci, i, "doing", 0, None)
                    t0 = time.time()
                    r = _orig(action, target, value, step)
                    shot = None
                    if opts.get("shots", True):
                        try:
                            shot = out_dir / f"{case['id']}_step{i + 1:02d}.png"
                            _bp.page.screenshot(path=str(shot), timeout=4000)
                            _res["shots"].append(shot.name)
                        except Exception:  # noqa: BLE001
                            shot = None
                    on_step(_ci, i, "ok", round(time.time() - t0, 1), shot.name if shot else None)
                    return r
                runner._dispatch = dispatch
                t0 = time.time()
                try:
                    runner.run(steps)
                except (TradeMismatch, SettingLocked, FeatureOff) as e:
                    res.update(outcome="skipped", error=str(e)[:600])
                except StepFailed as e:
                    res.update(outcome="failed", error=str(e)[:1200], failed_step=state_i["i"])
                except BaseException as e:  # noqa: BLE001  (pytest.skip etc. raise Skipped)
                    if type(e).__name__ in ("Skipped", "Exit"):
                        res.update(outcome="skipped", error=str(e)[:600])
                    else:
                        res.update(outcome="failed", error=str(e)[:1200], failed_step=state_i["i"])
                res["seconds"] = round(time.time() - t0, 1)
                if res["outcome"] == "failed":
                    fi = max(res["failed_step"], 0)
                    shot = out_dir / f"{case['id']}_FAIL.png"
                    try:
                        bp.page.screenshot(path=str(shot), timeout=4000)
                        res["shots"].append(shot.name)
                    except Exception:  # noqa: BLE001
                        pass
                    on_step(ci, fi, "bad", res["seconds"], shot.name)
                    for j in range(fi + 1, len(steps)):
                        on_step(ci, j, "skip", 0, None)
                    if opts.get("stop_first"):
                        break
                else:
                    for j in range(state_i["i"] + 1, len(steps)):
                        on_step(ci, j, "skip" if res["outcome"] == "skipped" else "ok", 0, None)
                ensure_neutral(bp)
        finally:
            try:
                if opts.get("trace", True):
                    ctx.tracing.stop(path=str(out_dir / "trace.zip"))
            except Exception:  # noqa: BLE001
                pass
            vpath = None
            try:
                vid = ctx.pages[0].video if ctx.pages else None
                ctx.close()
                if vid:
                    vpath = vid.path()
            except Exception:  # noqa: BLE001
                pass
            browser.close()
            if vpath and Path(vpath).exists():
                shutil.move(str(vpath), str(out_dir / "run.webm"))
    return results


# ================================================================= diagnose

def diagnose(err: str, step_text: str = "") -> dict:
    """Plain-words reason for a failure. A disabled field is a Control Room setting, not a code problem."""
    e = err or ""
    m = re.search(r"strict mode violation", e)
    if m:
        return {"plain": "More than one place on the screen matched, so the click was ambiguous.", "setting": ""}
    if re.search(r"disabled|not enabled|readonly", e, re.I):
        name = (re.search(r"(?:step \d+ failed: )?([\w .%]+?)(?: field)?\b", step_text or "").group(1)
                if step_text else "")
        setting = ""
        try:
            from framework import control_room
            key = control_room.find_by_phrase(name or "")
            if key:
                setting = key
        except Exception:  # noqa: BLE001
            pass
        txt = ("The field is disabled. " + (f"This depends on the Control Room setting “{setting}”, "
               "so it is a setting, not a code problem. Run “Learn the app” to turn trade settings on."
               if setting else "A Control Room setting may be switched off for this company."))
        return {"plain": txt, "setting": setting or "unknown"}
    if re.search(r"covered by|intercepts pointer", e, re.I):
        return {"plain": "Another window (for example the Batch window) opened and covered the next box.", "setting": ""}
    if re.search(r"Timeout|not found|nahi mila|waiting for", e, re.I):
        return {"plain": "The element was not found in time. Its locator may have changed.", "setting": ""}
    return {"plain": "The step failed. The exact message is below.", "setting": ""}


_LOC = re.compile(r"""locator\('((?:[^'\\]|\\.)*)'\)""")


def _memory_ok(line: str) -> bool:
    """An AI-written line may only use locators that exist in app memory (or none at all)."""
    sels = {f["sel"] for s in memory.build()["screens"].values() for f in s["fields"]}
    return all(script.unq(x) in sels for x in _LOC.findall(line))


def ai_fix(job: dict, fail_line: int, err: str) -> tuple[bool, str]:
    """Ask AI for a replacement of ONE line. Sends: the error, 3 lines around it, matching memory entries."""
    lines = job["code"].split("\n")
    if fail_line < 0 or fail_line >= len(lines):
        return False, "The failing line could not be located in the script."
    around = "\n".join(lines[max(0, fail_line - 3): fail_line + 4])
    words = set(re.findall(r"[A-Za-z]{3,}", lines[fail_line] + " " + err[:200]))
    fields = []
    for sname, s in memory.build()["screens"].items():
        for f in s["fields"]:
            if any(w.lower() in f["name"].lower() or w.lower() in f["sel"].lower() for w in words):
                fields.append(f"{sname} / {f['name']}: {f['sel']}")
    fields = fields[:12]
    try:
        ans, tok, cached = state.ai_json(
            "replay.fix",
            "You fix ONE failing Playwright line. Use only locators from the given list. "
            "Never change expected values or assertions. Reply JSON {\"line\":\"<the full replacement line>\","
            "\"why\":\"<one short sentence>\"}.",
            f"error: {err[:500]}\ncode around the failing line (line {fail_line - max(0, fail_line - 3) + 1}):\n{around}\n"
            f"known fields:\n" + "\n".join(fields), 500, job.get("case_id", ""))
    except Exception as e:  # noqa: BLE001
        return False, str(e)
    new = str((ans or {}).get("line", "")).rstrip()
    if not new.strip().startswith("await") or "expect(" in lines[fail_line] != ("expect(" in new):
        return False, "AI did not return a usable line, or it tried to change a check."
    if not new.startswith(" "):
        new = "  " + new
    if not _memory_ok(new):
        return False, "AI used a locator that is not in app memory, so the answer was rejected."
    job["tokens"]["ai"] += tok
    job["fixText"] = (ans or {}).get("why", "")
    job["fixedLines"].append(new.strip())
    lines[fail_line] = new
    job["code"] = "\n".join(lines)
    return True, new


# ==================================================================== replay

def start_replay(code: str, name: str, module: str, author: str) -> str:
    jid = _new_id("r")
    s = state.load_settings()
    JOBS[jid] = {"id": jid, "kind": "replay", "state": "queued", "attempt": 0, "max": s["fix_attempts"],
                 "aiFixes": 0, "steps": [], "err": None, "code": code, "fixedLines": [], "giveUp": False,
                 "tokens": {"local": 0, "ai": 0}, "log": "", "name": name, "module": module, "author": author,
                 "case_id": "", "fixText": "", "dir": str(RUNS_DIR / f"replay_{jid}")}
    threading.Thread(target=_replay_thread, args=(jid,), daemon=True).start()
    return jid


def retry(jid: str) -> str:
    j = JOBS.get(jid)
    if not j:
        raise KeyError("replay not found")
    j.update(state="queued", giveUp=False, err=None, attempt=0, aiFixes=0)
    threading.Thread(target=_replay_thread, args=(jid,), daemon=True).start()
    return jid


def _step_text(st: dict) -> str:
    return st.get("note") or f"{st.get('action')} {st.get('target') or ''} {st.get('value') or ''}".strip()


def _replay_thread(jid: str, play=None):
    job = JOBS[jid]
    play = play or _play
    try:
        while True:
            job["attempt"] += 1
            job["state"] = "running"
            conv = script.to_steps(job["code"])
            steps = conv["steps"]
            job["steps"] = [{"text": _step_text(s), "status": "todo", "secs": 0} for s in steps]
            if conv["unknown"] or not steps:
                u = conv["unknown"]
                job.update(state="failed", giveUp=True, err={
                    "plain": (f"{len(u)} line(s) in the script cannot be replayed." if u else "The script has no actions."),
                    "err": "\n".join(f"line {x['line']}: {x['text']}  → {x['why']}" for x in u),
                    "lineText": u[0]["text"] if u else "", "fixText": ""})
                return
            lines = job["code"].split("\n")

            def on_step(ci, si, status, secs, shot, _j=job):
                if 0 <= si < len(_j["steps"]):
                    _j["steps"][si].update(status=status, secs=secs)

            with _browser_lock:
                res = play([{"id": "REPLAY", "name": job["name"], "steps": steps,
                             "destructive": any(s.get("destructive") for s in steps) or _writes(steps)}],
                           {"dir": job["dir"], "label": "replay " + jid, "video": False, "shots": False, "trace": False},
                           on_step, lambda m: _log(job, m))[0]
            if res["outcome"] == "passed":
                job.update(state="passed", err=None)
                return
            if res["outcome"] == "skipped":
                job.update(state="failed", giveUp=True, err={"plain": res["error"] or "The test was skipped.",
                                                              "err": res["error"] or "", "lineText": "", "fixText": ""})
                return
            fi = res["failed_step"]
            st = steps[fi] if 0 <= fi < len(steps) else {}
            line_no = _locate(lines, st, conv)
            dg = diagnose(res["error"] or "", _step_text(st))
            job["err"] = {"plain": dg["plain"], "err": res["error"] or "", "lineText": lines[line_no].strip() if 0 <= line_no < len(lines) else "",
                          "fixText": ""}
            job["tokens"]["local"] += 1
            if dg["setting"]:
                job.update(state="failed", giveUp=True)       # a setting, not code: AI cannot fix it
                return
            if job["aiFixes"] >= job["max"]:
                job.update(state="failed", giveUp=True)
                return
            job["state"] = "fixing"
            ok, msg = ai_fix(job, line_no, res["error"] or "")
            if not ok:
                job["err"]["fixText"] = msg
                job.update(state="failed", giveUp=True)
                return
            job["aiFixes"] += 1
            job["err"]["fixText"] = job.get("fixText") or msg.strip()
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()[-900:]
        job.update(state="failed", giveUp=True, err={"plain": start_error(e, tb), "err": tb, "lineText": "", "fixText": ""})


def start_error(e: Exception, tb: str = "") -> str:
    """Plain words for 'the browser part could not even start'."""
    low = (str(e) + tb).lower()
    if "executable doesn't exist" in low or "playwright install" in low:
        return "The Playwright browser is not installed on this PC. Run: python -m playwright install chromium"
    if "no module named" in low and "playwright" in low:
        return "Playwright is not installed. Run setup.bat first."
    if "login" in low or "sign" in low or "password" in low:
        return "Could not sign in. Check the URL, user and password in Settings, then press Test login."
    return "Could not start the browser run."


def _writes(steps: list[dict]) -> bool:
    return any(s.get("action") in ("save_form", "set_party", "add_item", "bulk_sale_bills", "retail_bill") for s in steps)


def _locate(lines: list[str], step: dict, conv: dict) -> int:
    """Script line number (0-based) of the action that produced this step."""
    ln = step.get("_line")
    if ln:
        return ln - 1
    return -1


def replay_status(jid: str) -> dict:
    j = JOBS.get(jid)
    if not j:
        raise KeyError("replay not found")
    keys = ("state", "attempt", "max", "aiFixes", "steps", "err", "code", "fixedLines", "tokens", "giveUp", "log")
    return {k: j[k] for k in keys}


# ====================================================================== run

def start_run(ids: list[str], opts: dict, who: str = "") -> str:
    rid = _new_id("R-")
    JOBS[rid] = {"id": rid, "kind": "run", "state": "queued", "title": "Queued", "total": 0, "done": 0, "steps": [],
                 "current": None, "results": [], "seconds": 0, "who": who, "ids": ids, "opts": opts,
                 "dir": str(RUNS_DIR / f"run_{rid}"), "log": ""}
    threading.Thread(target=_run_thread, args=(rid,), daemon=True).start()
    return rid


def _run_thread(rid: str, play=None):
    from ui_studio import tests
    job, play, t0 = JOBS[rid], play or _play, time.time()
    try:
        cases = tests.load_cases(job["ids"])
        job.update(state="running", total=len(cases))
        shown = {"ci": -1}

        def on_step(ci, si, status, secs, shot):
            if shown["ci"] != ci:
                shown["ci"] = ci
                c = cases[ci]
                job["current"] = {"id": c["id"], "name": c["name"]}
                job["title"] = f"{c['display_id']} · {c['name']}"
                job["steps"] = [{"text": _step_text(s), "status": "todo", "secs": 0} for s in c["steps"]]
            if 0 <= si < len(job["steps"]):
                job["steps"][si].update(status=status, secs=secs)
            job["seconds"] = round(time.time() - t0, 1)
        o = {"dir": job["dir"], "label": rid, "video": job["opts"].get("video", True),
             "shots": job["opts"].get("shots", True), "trace": job["opts"].get("bugpack", True),
             "stop_first": job["opts"].get("stop_first", False)}
        # one browser run per test keeps each test's steps, video and trace separate
        all_res = []
        for ci, c in enumerate(cases):
            sub = dict(o, dir=str(Path(job["dir"]) / c["id"]))
            with _browser_lock:
                shown["ci"] = -1
                r = play([c], sub, lambda _ci, si, st, sc, sh, _real=ci: on_step(_real, si, st, sc, sh),
                         lambda m: _log(job, m))
            res = r[0] if r else {"outcome": "failed", "error": "No result", "failed_step": 0, "shots": [], "seconds": 0}
            n = len(c["steps"])
            passed = sum(1 for s in job["steps"] if s["status"] == "ok") if shown["ci"] == ci else (n if res["outcome"] == "passed" else 0)
            record = _save_run(job, c, res, [dict(s) for s in job["steps"]], passed)
            job["results"].append(record)
            job["done"] += 1
            all_res.append(res)
            if res["outcome"] == "failed" and o["stop_first"]:
                break
        job.update(state="done", title="Run finished", seconds=round(time.time() - t0, 1))
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()[-900:]
        job.update(state="error", title="Run stopped: " + start_error(e, tb), seconds=round(time.time() - t0, 1))
        _log(job, tb)


def _save_run(job: dict, c: dict, res: dict, steps: list[dict], passed: int) -> dict:
    import json
    seq = _next_run_seq()
    rid = f"R-{seq:04d}"
    result = {"passed": "Pass", "failed": "Fail", "skipped": "Skip"}[res["outcome"]]
    for s in steps:
        if s["status"] == "todo":
            s["status"] = "skip"
    row = {"id": rid, "test_id": c["display_id"], "name": c["name"], "module": c["module"], "author": c["author"],
           "at": time.strftime("%d-%b-%Y %H:%M"), "passed": passed if res["outcome"] != "passed" else len(steps),
           "total": len(steps), "result": result, "err": res.get("error") or "",
           "fail_at": res.get("failed_step", -1), "steps": json.dumps(steps),
           "dir": str(Path(job["dir"]) / c["id"]), "ai_fixes": 0, "ts": time.time()}
    with state.db() as con:
        con.execute("INSERT OR REPLACE INTO runs VALUES(:id,:test_id,:name,:module,:author,:at,:passed,:total,:result,"
                    ":err,:fail_at,:steps,:dir,:ai_fixes,:ts)", row)
    return {"run_id": rid, "test": c["display_id"], "result": result, "passed": row["passed"], "total": row["total"],
            "err": row["err"], "failAt": row["fail_at"]}


def _next_run_seq() -> int:
    with state.db() as con:
        r = con.execute("SELECT COALESCE(MAX(CAST(SUBSTR(id,3) AS INTEGER)),0)+1 n FROM runs").fetchone()
    return int(r["n"])


def run_status(rid: str) -> dict:
    j = JOBS.get(rid)
    if not j:
        raise KeyError("run not found")
    return {k: j[k] for k in ("state", "title", "total", "done", "steps", "current", "results", "seconds", "log")}
