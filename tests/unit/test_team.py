"""Admin Team view: people, coverage, failures and activity from what the Studio stores."""
import json
import time

import pytest

from ui_studio import state, team, tests


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(tests, "list_tests", lambda: [
        {"id": "TC_A", "module": "Sale", "steps": 5, "scripts": 0, "draft": False},
        {"id": "TC_B", "module": "Sale", "steps": 0, "scripts": 1, "draft": True},
        {"id": "TC_C", "module": "Sale", "steps": 0, "scripts": 0, "draft": True},
        {"id": "TC_D", "module": "Masters", "steps": 3, "scripts": 0, "draft": False}])
    now = time.time()
    side = json.dumps({"what": "x", "side": "app"})
    with state.db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT, name TEXT, role TEXT, pw TEXT, disabled INT, "
                  "mb_user TEXT, mb_secret TEXT, created TEXT, last_login TEXT)")
        c.execute("INSERT INTO users VALUES('qa1@qa.test','Asha','qa','',0,'a@x.in','s','','24-Nov-2026 10:00')")
        c.execute("INSERT INTO users VALUES('boss@qa.test','Boss','admin','',0,'','','','')")
        for i, (tid, res, who, ts, ex) in enumerate([("TC_A", "Pass", "qa1@qa.test", now, ""), ("TC_A", "Fail", "qa1@qa.test", now - 60, side),
                                                     ("TC_D", "Fail", "qa1@qa.test", now - 120, ""),
                                                     ("TC_A", "Pass", "", now - 40 * 86400, "")]):
            c.execute("INSERT INTO runs(id,test_id,name,module,author,at,passed,total,result,err,fail_at,steps,dir,"
                      "ai_fixes,ts,run_by,explain) VALUES(?,?,?,?,?,?,0,1,?,?,0,'[]','',0,?,?,?)",
                      (f"R-{i}", tid, "n", "Sale", "a", "", res, "Not visible: x" if res == "Fail" else "", ts, who, ex))
        c.execute("INSERT INTO tests(id,name,module,author,priority,description,kind,created,seq) "
                  "VALUES('TC-1','t','Sale','Asha','Medium','','written',?,1)", (time.strftime("%d-%b-%Y"),))
    team.log("qa1@qa.test", "script_written", "TC_B", "tests/x.py::test_b (AI)")
    from ui_studio import feedback
    feedback.add({"kind": "studio", "text": "Replay stuck", "test": "TC_A"}, "qa1@qa.test", "Asha")
    return now


def test_people_coverage_failures_and_activity(db):
    d = team.overview("7")
    asha = next(p for p in d["people"] if p["name"] == "Asha")
    assert (asha["runs"], asha["passed"], asha["failed"], asha["tests_written"], asha["scripts_written"],
            asha["feedback"], asha["feedback_open"], asha["mb_login"]) == (3, 1, 2, 1, 1, 1, 1, True)
    boss = next(p for p in d["people"] if p["name"] == "Boss")
    assert boss["runs"] == 0 and boss["role"] == "admin" and boss["mb_login"] is False    # listed though idle
    k = d["kpis"]
    assert (k["cases"], k["covered"], k["coverage"], k["runs"], k["pass_rate"], k["flaky"]) == (4, 3, 75, 3, 33, 1)
    sale = next(m for m in d["modules"] if m["module"] == "Sale")
    assert (sale["total"], sale["covered"], sale["automated"], sale["scripts"], sale["never_run"]) == (3, 2, 1, 1, 1)
    sides = {s["side"]: s["count"] for s in d["failures"]["by_side"]}
    assert sides["app"] == 1 and sum(sides.values()) == 2                    # the older one is classified now
    assert d["failures"]["most_failed"][0]["test"] in ("TC_A", "TC_D") and d["failures"]["flaky"][0]["test"] == "TC_A"
    kinds = {a["kind"] for a in d["activity"]}
    assert {"run", "test", "feedback", "script_written"} <= kinds


def test_period_all_time_includes_older_runs(db):
    assert team.overview("")["kpis"]["runs"] == 4 and team.overview("7")["kpis"]["runs"] == 3


def test_only_an_admin_sees_the_team(tmp_path, monkeypatch):
    from tests.unit.test_studio_server_mode import _call, _client, srv  # noqa: F401
    from ui_studio import accounts, mode, server
    import threading
    from http.server import ThreadingHTTPServer
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "s.json")
    monkeypatch.setattr(mode, "SERVER", True)
    monkeypatch.setattr(mode, "SECURE_COOKIE", False)
    monkeypatch.setattr(tests, "list_tests", lambda: [])
    s = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{s.server_address[1]}"
    accounts.create_user("boss@qa.test", "password123", "admin", "Boss")
    accounts.create_user("qa1@qa.test", "password123", "qa", "QA One")
    try:
        qa, boss = _client(), _client()
        _call(qa, base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"})
        _call(boss, base, "/api/auth/login", {"username": "boss@qa.test", "password": "password123"})
        assert _call(qa, base, "/api/team?days=7")[0] == 403
        code, d, _ = _call(boss, base, "/api/team?days=7")
        assert code == 200 and {p["name"] for p in d["people"]} >= {"Boss", "QA One"}
    finally:
        s.shutdown()
