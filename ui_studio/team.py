"""
Team view for the admin: who did what, how much of the app is covered, what fails and why.

What a QA lead looks at in test-management tools (TestRail workload / activity summary, Xray coverage and
execution-by-assignee, ReportPortal / BrowserStack failure categories, most-failed and flaky tests), from the data
Test Studio keeps:
  * tests (who wrote / recorded each), runs (who ran it, result, failure summary and its side), feedback,
    Studio accounts (role, last login, own MargBooks login), the test-case catalogue (automated / Python script),
    and `activity` (events no other table records, e.g. "Write as a script").
Everything is read-only here; nothing is computed by AI.
"""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from datetime import datetime

from ui_studio import state


def _schema(con):
    con.execute("CREATE TABLE IF NOT EXISTS activity(ts REAL, who TEXT, kind TEXT, ref TEXT, detail TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS activity_ts ON activity(ts)")


state.add_schema(_schema)

PERIODS = {"1": 1, "7": 7, "30": 30, "": 0}
SIDE_NAMES = {"test": "Test needs a change", "app": "Possible app bug", "setup": "Test data / company setup",
              "login": "Login / environment", "studio": "Test Studio", "": "Not classified"}


def log(who: str, kind: str, ref: str = "", detail: str = "") -> None:
    """Record an event no other table keeps (who wrote a Python script with "Write as a script", ...)."""
    try:
        with state.db() as c:
            c.execute("INSERT INTO activity VALUES(?,?,?,?,?)", (time.time(), who or "", kind, ref, detail[:300]))
    except Exception:  # noqa: BLE001  (the team view must never break the action it records)
        pass


def _date_ts(text: str) -> float:
    for fmt in ("%d-%b-%Y %H:%M", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(text or "").strip(), fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _when(value) -> str:
    """A stored time (seconds since 1970, or already text) as dd-Mon-yyyy hh:mm."""
    try:
        return time.strftime("%d-%b-%Y %H:%M", time.localtime(float(value))) if value not in (None, "") else ""
    except (TypeError, ValueError):
        return str(value)


def _rows(sql: str, args=()) -> list[dict]:
    try:
        with state.db() as c:
            return [dict(r) for r in c.execute(sql, args)]
    except Exception:  # noqa: BLE001  (a table a fresh database does not have yet)
        return []


def overview(days: str = "7") -> dict:
    from ui_studio import tests
    span = PERIODS.get(str(days), 7)
    since = time.time() - span * 86400 if span else 0.0
    users = _rows("SELECT username, name, role, disabled, mb_user, last_login, created FROM users")
    name_of = {u["username"]: (u["name"] or u["username"]) for u in users}
    who = lambda key: name_of.get(key or "", key or "") or "Unknown"      # noqa: E731  username or name -> name

    runs = _rows("SELECT id, test_id, name, module, author, at, result, err, ts, run_by, explain FROM runs")
    wrote = _rows("SELECT id, name, module, author, kind, created FROM tests")
    fb = _rows("SELECT id, ts, by_user, by_name, kind, test, status FROM feedback")
    act = _rows("SELECT ts, who, kind, ref, detail FROM activity")
    cases = tests.list_tests()

    in_span = lambda ts: (ts or 0) >= since                                  # noqa: E731
    p_runs = [r for r in runs if in_span(r["ts"])]
    p_wrote = [t for t in wrote if in_span(_date_ts(t["created"]))]
    p_fb = [f for f in fb if in_span(f["ts"])]
    p_act = [a for a in act if in_span(a["ts"])]

    # ---------------------------------------------------------------- people (TestRail "workload / activity")
    people: dict[str, dict] = defaultdict(lambda: {"tests_written": 0, "tests_recorded": 0, "scripts_written": 0,
                                                    "runs": 0, "passed": 0, "failed": 0, "other": 0, "feedback": 0,
                                                    "feedback_open": 0, "last_active": 0.0})

    def touch(name: str, ts: float):
        p = people[name]
        p["last_active"] = max(p["last_active"], ts or 0.0)
        return p

    for t in p_wrote:
        p = touch(who(t["author"]), _date_ts(t["created"]))
        p["tests_recorded" if t["kind"] == "record" else "tests_written"] += 1
    for r in p_runs:
        p = touch(who(r["run_by"]) if r["run_by"] else "Unknown (older runs)", r["ts"])
        p["runs"] += 1
        p["passed" if r["result"] == "Pass" else "failed" if r["result"] == "Fail" else "other"] += 1
    for f in p_fb:
        p = touch(who(f["by_user"]) if f["by_user"] else (f["by_name"] or "Unknown"), f["ts"])
        p["feedback"] += 1
        p["feedback_open"] += f["status"] in ("open", "in_progress")
    for a in p_act:
        p = touch(who(a["who"]), a["ts"])
        if a["kind"] == "script_written":
            p["scripts_written"] += 1
    for u in users:                                  # every account is listed, also one that did nothing yet
        p = people[u["name"] or u["username"]]
        p.update(username=u["username"], role=u["role"], disabled=bool(u["disabled"]),
                 mb_login=bool(u["mb_user"]), last_login=_when(u["last_login"]))
    people_list = []
    for name, p in people.items():
        done = p["passed"] + p["failed"]
        people_list.append({"name": name, "role": p.get("role", ""), "username": p.get("username", ""),
                            "disabled": p.get("disabled", False), "mb_login": p.get("mb_login"),
                            "last_login": p.get("last_login", ""),
                            "last_active": time.strftime("%d-%b-%Y %H:%M", time.localtime(p["last_active"]))
                            if p["last_active"] else "",
                            "pass_rate": round(p["passed"] / done * 100) if done else None,
                            **{k: p[k] for k in ("tests_written", "tests_recorded", "scripts_written", "runs",
                                                 "passed", "failed", "other", "feedback", "feedback_open")}})
    people_list.sort(key=lambda x: (-(x["runs"] + x["tests_written"] + x["tests_recorded"] + x["scripts_written"]),
                                    x["name"]))

    # ---------------------------------------------------------------- coverage (catalogue + latest result)
    latest: dict[str, dict] = {}
    for r in sorted(runs, key=lambda r: r["ts"] or 0):
        latest[r["test_id"]] = r
    by_mod: dict[str, dict] = defaultdict(lambda: Counter())
    for t in cases:
        m = by_mod[t["module"] or "Other"]
        m["total"] += 1
        auto, script = bool(t["steps"]) and not t.get("draft"), bool(t.get("scripts"))
        m["automated"] += auto
        m["scripts"] += script
        m["covered"] += auto or script
        last = latest.get(t["id"])
        if last:
            m["ran"] += 1
            m["last_pass" if last["result"] == "Pass" else "last_fail" if last["result"] == "Fail" else "last_other"] += 1
        elif auto or script:
            m["never_run"] += 1
    modules = [{"module": k, **{x: v.get(x, 0) for x in ("total", "automated", "scripts", "covered", "ran",
                                                          "last_pass", "last_fail", "last_other", "never_run")},
                "coverage": round(v["covered"] / v["total"] * 100) if v["total"] else 0}
               for k, v in by_mod.items()]
    modules.sort(key=lambda m: (-m["total"], m["module"]))
    total = sum(m["total"] for m in modules)
    covered = sum(m["covered"] for m in modules)

    # ---------------------------------------------------------------- failures (categories, most failed, flaky)
    from ui_studio.explain import explain
    sides: Counter = Counter()
    for r in p_runs:
        if r["result"] in ("Fail", "Blocked"):
            try:
                side = (json.loads(r["explain"] or "{}") or {}).get("side", "")
            except ValueError:
                side = ""
            sides[side or explain(r["err"] or "", "", r["result"]).get("side", "")] += 1   # older runs: made now
    per_test: dict[str, list] = defaultdict(list)
    for r in sorted(p_runs, key=lambda r: r["ts"] or 0):
        per_test[r["test_id"]].append(r)
    most_failed = sorted(({"test": k, "name": v[-1]["name"], "module": v[-1]["module"], "runs": len(v),
                           "failed": sum(1 for r in v if r["result"] == "Fail"), "last": v[-1]["result"],
                           "last_run": v[-1]["id"]} for k, v in per_test.items()),
                         key=lambda x: (-x["failed"], -x["runs"]))
    flaky = [x | {"passed": x["runs"] - x["failed"]} for x in most_failed
             if x["failed"] and any(r["result"] == "Pass" for r in per_test[x["test"]])]

    # ---------------------------------------------------------------- activity feed (newest first)
    feed = ([{"ts": r["ts"] or 0, "who": who(r["run_by"]) if r["run_by"] else "Unknown", "what": f"ran {r['test_id']}",
              "detail": r["result"], "ref": r["id"], "kind": "run"} for r in p_runs]
            + [{"ts": _date_ts(t["created"]), "who": who(t["author"]),
                "what": f"{'recorded' if t['kind'] == 'record' else 'wrote'} {t['id']}", "detail": t["name"],
                "ref": t["id"], "kind": "test"} for t in p_wrote]
            + [{"ts": f["ts"], "who": who(f["by_user"]) if f["by_user"] else f["by_name"],
                "what": f"gave feedback FB-{int(f['id']):04d}", "detail": f["kind"], "ref": f["test"] or "",
                "kind": "feedback"} for f in p_fb]
            + [{"ts": a["ts"], "who": who(a["who"]), "what": a["kind"].replace("_", " ") + f" {a['ref']}",
                "detail": a["detail"], "ref": a["ref"], "kind": a["kind"]} for a in p_act])
    feed.sort(key=lambda x: -x["ts"])
    for x in feed:
        x["at"] = time.strftime("%d-%b %H:%M", time.localtime(x["ts"])) if x["ts"] else ""

    passed = sum(1 for r in p_runs if r["result"] == "Pass")
    failed = sum(1 for r in p_runs if r["result"] == "Fail")
    return {
        "period": str(days), "since": time.strftime("%d-%b-%Y", time.localtime(since)) if since else "",
        "kpis": {"cases": total, "covered": covered, "coverage": round(covered / total * 100) if total else 0,
                 "automated": sum(m["automated"] for m in modules), "scripts": sum(m["scripts"] for m in modules),
                 "new_tests": len(p_wrote), "runs": len(p_runs), "passed": passed, "failed": failed,
                 "pass_rate": round(passed / (passed + failed) * 100) if passed + failed else None,
                 "flaky": len(flaky), "feedback_open": sum(1 for f in fb if f["status"] in ("open", "in_progress")),
                 "feedback_new": len(p_fb),
                 "active_qas": sum(1 for p in people_list if p["runs"] or p["tests_written"] or p["tests_recorded"]
                                   or p["scripts_written"] or p["feedback"]),
                 "accounts": len(users)},
        "people": people_list, "modules": modules,
        "failures": {"by_side": [{"side": k, "label": SIDE_NAMES.get(k, k), "count": v} for k, v in sides.most_common()],
                     "most_failed": [x for x in most_failed if x["failed"]][:10], "flaky": flaky[:10]},
        "activity": feed[:60],
    }
