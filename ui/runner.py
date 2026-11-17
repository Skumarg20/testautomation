"""
Test chalane wala worker.

Ek waqt me ek hi test chalta hai (ek browser hai). Baaki qatar me lagte hain.
UI har second pooch kar live progress dikhata hai.
"""
from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid

from config.settings import settings

RUNS: dict[str, dict] = {}
_Q: "queue.Queue[str]" = queue.Queue()
_worker: threading.Thread | None = None
_lock = threading.Lock()


def submit(case_ids: list[str], who: str = "") -> str:
    """Qatar me lagao, run_id wapas do."""
    rid = uuid.uuid4().hex[:8]
    RUNS[rid] = {
        "id": rid, "cases": case_ids, "who": who,
        "status": "queued", "started": None, "finished": None,
        "current": None, "log": [], "results": [], "artifacts": None,
        "position": _Q.qsize() + 1,
    }
    _Q.put(rid)
    _ensure_worker()
    return rid


def get(rid: str) -> dict | None:
    return RUNS.get(rid)


def recent(n: int = 20) -> list[dict]:
    rs = sorted(RUNS.values(), key=lambda r: r.get("started") or 0, reverse=True)
    return [{k: v for k, v in r.items() if k != "log"} for r in rs[:n]]


def _ensure_worker():
    global _worker
    with _lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_loop, daemon=True)
            _worker.start()


def _log(run: dict, text: str, kind: str = "info"):
    run["log"].append({"t": round(time.time(), 1), "kind": kind, "text": text})


def _loop():
    while True:
        try:
            rid = _Q.get(timeout=300)
        except queue.Empty:
            return
        run = RUNS.get(rid)
        if not run:
            continue
        try:
            _run_one(run)
        except Exception:  # noqa: BLE001
            run["status"] = "error"
            _log(run, traceback.format_exc()[-1500:], "fail")
        finally:
            run["finished"] = time.time()
            _Q.task_done()


def _run_one(run: dict):
    from playwright.sync_api import sync_playwright
    from framework import safety, netguard, event_recorder
    from framework.auth import login, app_ready
    from framework.browser import launch
    from framework.step_runner import (StepRunner, RunContext, StepFailed,
                                       TradeMismatch)
    from framework.screens_check import ensure_neutral
    from framework.control_room import FeatureOff, SettingLocked
    from framework import control_room
    from framework import autolearn, catalogue, heal, logbook
    from ui import store, envs

    run["status"] = "running"
    run["started"] = time.time()

    # Chuna hua environment lagao -- UAT/prod/staging jo bhi UI me select hai.
    env = envs.apply_active()
    if env:
        run["env"] = {"name": env.get("name"), "app_url": env.get("app_url"),
                      "writes": bool(env.get("allow_writes"))}
    artifacts = settings.init_run(f"UI run {run['id']}")
    run["artifacts"] = str(artifacts)

    safety.CLICK_LOG.clear()      # har run ka apna hisaab, pichhle ka mila hua nahi
    netguard.BLOCKED.clear()

    cases = [c for c in store.list_all() if c.id in run["cases"]]
    # Kuch test jaan-boojh kar logout karte hain (galat password wale). Wo
    # session tod dete hain, isliye unhe SABSE AAKHIR me chalate hain -- warna
    # unke baad ke saare test bekaar fail hote hain.
    def breaks_session(c):
        if "breaks_session" in (c.tags or []):
            return True
        return any("logout" in str(st.get("target", "")).lower() for st in c.steps)
    cases = sorted(cases, key=breaks_session)
    if not cases:
        run["status"] = "error"
        _log(run, "No matching tests found", "fail")
        return

    _log(run, f"Running {len(cases)} test(s)"
              + (f" on {run['env']['name']} ({run['env']['app_url']})"
                 if run.get("env") else ""))
    if not settings.ALLOW_DESTRUCTIVE:
        writes = [c.id for c in cases if c.destructive]
        if writes:
            _log(run, f"{len(writes)} test(s) write data and will be SKIPPED. "
                      f"Turn on 'Allow writes' in Settings to run them.", "warn")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        try:
            _log(run, "Signing in...")
            bp = login(ctx.new_page())
            _log(run, "Signed in", "pass")

            # Control Room ek baar padh lo -- poora app usi par tika hai.
            # Iske bina pata hi nahi chalta ki test isliye fail hua ki bug
            # hai, ya isliye ki wo feature is company me band hai.
            try:
                cr = control_room.load()
                if not cr.get("read_at"):
                    _log(run, "Control Room padh rahe hain (pehli baar)...")
                    cr = control_room.capture(bp, verbose=False)
                    ensure_neutral(bp)
                run["control_room"] = control_room.summary()
                _log(run, "Settings: " + control_room.summary(), "ai")
            except Exception as e:  # noqa: BLE001
                _log(run, f"Control Room nahi padh paye: {str(e)[:150]}", "warn")

            for case in cases:
                run["current"] = {"id": case.id, "title": case.title,
                                  "expected": case.expected or [],
                                  "step": 0, "total": len(case.steps)}
                _log(run, f"--- {case.id}: {case.title}", "head")

                if getattr(case, "draft", False):
                    # Screen ka naksha hi nahi bana -- test likha hai par
                    # chalaya nahi ja sakta. Ye FAIL nahi hai.
                    why = next((p for p in (case.preconditions or [])
                                if p.startswith("DRAFT")), "screen not mapped yet")
                    _log(run, f"DRAFT — {why}", "skip")
                    run["results"].append({"id": case.id, "title": case.title,
                                           "outcome": "skipped", "reason": why})
                    continue

                if case.destructive and not settings.ALLOW_DESTRUCTIVE:
                    _log(run, "SKIPPED — this test writes data and "
                              "ALLOW_DESTRUCTIVE is false", "skip")
                    run["results"].append({"id": case.id, "title": case.title,
                                           "outcome": "skipped",
                                           "reason": "writes data"})
                    continue

                # Pichhle test ne session tod diya ho to dobara login karo.
                # Ye har test se pehle hota hai, isliye ek test ke fail hone se
                # baaki sab girte nahi.
                if not app_ready(bp.page, 4000):
                    _log(run, "Session khatam ho gaya tha -- dobara login", "warn")
                    bp = login(ctx.new_page())

                ensure_neutral(bp)
                t0 = time.time()
                ctxv = RunContext()
                runner = StepRunner(bp, ctxv)

                # har step ka live update
                orig = runner._dispatch

                def dispatch(action, target, value, step, _c=case):
                    run["current"]["step"] += 1
                    desc = step.get("note") or f"{action} {target or ''} {value or ''}"
                    run["current"]["doing"] = desc.strip()
                    _log(run, f"  [{run['current']['step']}/{len(_c.steps)}] {desc.strip()}")
                    return orig(action, target, value, step)

                runner._dispatch = dispatch

                try:
                    runner.run(case.steps)
                    outcome, err = "passed", None
                    _log(run, f"PASS  {case.id}", "pass")
                except StepFailed as e:
                    if getattr(case, "known_issue", False):
                        # Ye pehle se pata hui app ki kami hai. Ise laal dikhana
                        # rozana ke suite ko bekaar kar deta hai -- par chhupana
                        # bhi galat hai. Isliye alag bucket.
                        outcome, err = "known_issue", str(e)[:600]
                        _log(run, f"KNOWN ISSUE  {case.id} -- app ki jaanchi hui kami",
                             "warn")
                    else:
                        outcome, err = "failed", str(e)[:900]
                        _log(run, f"FAIL  {case.id}\n{err}", "fail")
                    bp.screenshot(f"ui_fail_{case.id}")
                except TradeMismatch as e:
                    # Test kisi aur trade ke liye hai -- app theek hai.
                    outcome, err = "skipped", str(e)[:400]
                    _log(run, f"SKIPPED  {case.id} -- doosre trade ka test", "skip")
                except SettingLocked as e:
                    # Test ko setting badalni thi par "Allow writes" OFF hai.
                    # App theek hai -- ijazat nahi hai. Isliye SKIP.
                    outcome, err = "skipped", str(e)[:400]
                    _log(run, f"SKIPPED  {case.id} -- setting badalne ki "
                              f"ijazat nahi", "skip")
                except FeatureOff as e:
                    # Control Room me feature band hai -- app theek hai, test
                    # chal hi nahi sakta. Ye FAIL nahi, SKIP hai.
                    outcome, err = "skipped", str(e)[:400]
                    _log(run, f"SKIPPED  {case.id} -- feature off in Control Room", "skip")
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                    if "skip" in msg.lower() or "not authorized" in msg.lower():
                        outcome, err = "skipped", msg[:400]
                        _log(run, f"SKIP  {case.id} -- {msg[:200]}", "skip")
                    else:
                        outcome, err = "failed", msg[:900]
                        _log(run, f"FAIL  {case.id}\n{msg[:400]}", "fail")
                        bp.screenshot(f"ui_fail_{case.id}")

                secs = round(time.time() - t0, 1)
                run["results"].append({
                    "id": case.id, "title": case.title, "outcome": outcome,
                    "seconds": secs, "error": err, "steps": ctxv.log,
                })
                # Disk par likh do -- server band hone par itihaas na ude
                logbook.record_result(case.id, outcome, secs, err or "",
                                      run_id=run["id"])
                logbook.write("execution", "test", outcome, test_id=case.id,
                              duration=secs, error=err or "")
                ensure_neutral(bp)

            # suraksha ki report
            if netguard.count():
                _log(run, f"{netguard.count()} delete request(s) BLOCKED", "warn")
            event_recorder.report(bp.page, artifacts / "events.log")
            # Agent ne is run me kya seekha -- do file me
            control_room.report(artifacts / "control_room.txt")
            ch = control_room.changed_report(artifacts / "settings_changed.txt")
            if ch:
                _log(run, f"{len(control_room.CHANGED)} Control Room setting "
                          f"badli gayi -- settings_changed.txt me dekh lo", "warn")
            cat_path = catalogue.report(artifacts / "element_catalogue.txt")
            cstats = catalogue.stats()
            if cstats.get("elements"):
                _log(run, f"Catalogue: {cstats['elements']} fields across "
                          f"{cstats['screens']} screens "
                          f"(see What it knows)", "ai")
            healed = heal.report(artifacts / "healed_locators.txt")
            if healed:
                _log(run, f"AI ne {len(heal.HEALED)} locator theek kiye -- "
                          f"healed_locators.txt me dekh lo", "ai")
            learned = autolearn.report(artifacts / "learned_locators.txt")
            if learned:
                _log(run, f"{len(autolearn.LEARNED)} naye locator khud seekhe -- "
                          f"learned_locators.txt me dekh lo", "warn")
            safety.delete_report(bp.page, artifacts / "delete_attempts.log")
            safety.flush_click_log()
        finally:
            browser.close()

    run["current"] = None
    n = lambda o: sum(1 for r in run["results"] if r["outcome"] == o)  # noqa: E731
    run["status"] = "done"
    known = n("known_issue")
    logbook.record_run(run["id"], run["results"], who=run.get("who", ""),
                       env=(run.get("env") or {}).get("name", ""))
    _log(run, f"Finished — {n('passed')} passed, {n('failed')} failed, "
              f"{n('skipped')} skipped"
              + (f", {known} known issue(s)" if known else ""), "head")
