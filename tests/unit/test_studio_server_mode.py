"""Test Studio server (team) mode: accounts, sessions, rights, CSRF, per-user runs and the run queue."""
from __future__ import annotations

import http.cookiejar
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from ui_studio import accounts, executor, mode, server, state


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "studio_settings.json")
    accounts._fails.clear()
    yield


# ---------------------------------------------------------------- accounts

def test_password_hash_and_check():
    h = accounts.hash_password("correct horse", rounds=1000)
    assert accounts.check_password("correct horse", h)
    assert not accounts.check_password("wrong", h)
    assert "correct horse" not in h


def test_margbooks_password_is_encrypted_at_rest():
    accounts.create_user("qa1@qa.test", "password123")
    accounts.set_margbooks_login("qa1@qa.test", "mb@example.com", "Very$ecret1")
    with state.db() as c:
        raw = c.execute("SELECT mb_secret FROM users WHERE username='qa1@qa.test'").fetchone()[0]
    assert raw and "Very$ecret1" not in raw
    assert accounts.margbooks_login("qa1@qa.test") == ("mb@example.com", "Very$ecret1")
    assert "Very$ecret1" not in json.dumps(accounts.get_user("qa1@qa.test"))
    accounts.set_margbooks_login("qa1@qa.test", "mb2@example.com", None)           # empty password keeps the saved one
    assert accounts.margbooks_login("qa1@qa.test") == ("mb2@example.com", "Very$ecret1")


def test_login_session_logout_and_disable():
    accounts.create_user("qa1@qa.test", "password123")
    tok, u = accounts.login("QA1@QA.test", "password123")             # the e-mail login ignores case
    assert u["username"] == "qa1@qa.test" and accounts.session_user(tok)["username"] == "qa1@qa.test"
    with state.db() as c:                                            # only the token's hash is stored
        assert not c.execute("SELECT 1 FROM sessions WHERE token=?", (tok,)).fetchone()
    accounts.logout(tok)
    assert accounts.session_user(tok) is None
    tok, _ = accounts.login("qa1@qa.test", "password123")
    accounts.create_user("boss@qa.test", "password123", "admin")
    accounts.update_user("qa1@qa.test", disabled=True)
    assert accounts.session_user(tok) is None
    with pytest.raises(accounts.AuthError):
        accounts.login("qa1@qa.test", "password123")


def test_wrong_passwords_lock_the_user_and_same_message_for_unknown_user():
    accounts.create_user("qa1@qa.test", "password123")
    msgs = set()
    for _ in range(accounts.MAX_FAILS):
        with pytest.raises(accounts.AuthError) as e:
            accounts.login("qa1@qa.test", "nope-nope")
        msgs.add(str(e.value))
    with pytest.raises(accounts.AuthError) as e:
        accounts.login("ghost", "nope-nope")
    msgs.add(str(e.value))
    assert len(msgs) == 1                                            # no username probing
    with pytest.raises(accounts.AuthError, match="Too many"):
        accounts.login("qa1@qa.test", "password123")


def test_last_admin_is_protected_and_weak_passwords_refused():
    accounts.create_user("boss@qa.test", "password123", "admin")
    with pytest.raises(accounts.AuthError):
        accounts.update_user("boss@qa.test", role="qa")
    with pytest.raises(accounts.AuthError):
        accounts.update_user("boss@qa.test", disabled=True)
    with pytest.raises(accounts.AuthError):
        accounts.create_user("qa2@qa.test", "short")
    with pytest.raises(accounts.AuthError):
        accounts.create_user("bad name!", "password123")


# ---------------------------------------------------------------- HTTP (server mode)

@pytest.fixture
def srv(monkeypatch):
    monkeypatch.setattr(mode, "SERVER", True)
    monkeypatch.setattr(mode, "SECURE_COOKIE", False)
    started = []
    monkeypatch.setattr(executor, "start_run", lambda ids, opts, who="", owner=None: started.append((who, owner)) or "R-x")
    s = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    accounts.create_user("boss@qa.test", "password123", "admin", "Boss")
    accounts.create_user("qa1@qa.test", "password123", "qa", "QA One")
    yield f"http://127.0.0.1:{s.server_address[1]}", started
    s.shutdown()


def _client():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def _call(op, base, path, body=None, headers=None):
    h = {"Content-Type": "application/json", "X-Studio": "1", **(headers or {})}
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers=h,
                                 method="GET" if body is None else "POST")
    try:
        r = op.open(req, timeout=20)
        return r.status, json.loads(r.read() or b"{}"), r.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


def test_everything_needs_a_login_except_the_page_and_health(srv):
    base, _ = srv
    op = _client()
    assert _call(op, base, "/api/state")[0] == 401
    assert _call(op, base, "/api/tests")[0] == 401
    assert _call(op, base, "/api/run", {"ids": ["X"]})[0] == 401
    assert _call(op, base, "/healthz")[0] == 200
    assert op.open(base + "/").status == 200
    code, _, hdr = _call(op, base, "/api/auth/state")
    assert code == 200 and hdr["X-Frame-Options"] == "DENY" and hdr["X-Content-Type-Options"] == "nosniff"


def test_cookie_is_httponly_and_samesite(srv):
    base, _ = srv
    code, d, hdr = _call(_client(), base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"})
    assert code == 200 and d["user"]["role"] == "qa"
    ck = hdr["Set-Cookie"]
    assert "HttpOnly" in ck and "SameSite=Strict" in ck and server.COOKIE in ck


def test_csrf_and_admin_rights(srv):
    base, _ = srv
    qa = _client()
    _call(qa, base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"})
    assert _call(qa, base, "/api/me/margbooks", {"user": "x"}, {"X-Studio": "0"})[0] == 403
    assert _call(qa, base, "/api/me/margbooks", {"user": "x"}, {"Origin": "http://evil.example"})[0] == 403
    for path in ("/api/settings", "/api/learn/start", "/api/code/read", "/api/scripts/save", "/api/users"):
        assert _call(qa, base, path, {})[0] == 403, path
    assert _call(qa, base, "/api/users")[0] == 403
    ad = _client()
    _call(ad, base, "/api/auth/login", {"username": "boss@qa.test", "password": "password123"})
    assert _call(ad, base, "/api/users")[0] == 200
    assert _call(ad, base, "/api/users", {"create": True, "username": "qa2@qa.test", "password": "password123"})[0] == 200


def test_run_uses_the_logged_in_users_own_margbooks_login(srv):
    base, started = srv
    qa = _client()
    _call(qa, base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"})
    code, d, _ = _call(qa, base, "/api/run", {"ids": ["TC_X"], "who": "Somebody Else"})
    assert code == 400 and "MargBooks login" in d["error"]
    assert _call(qa, base, "/api/me/margbooks", {"user": "qa1@mb", "password": "pw-1"})[0] == 200
    code, d, _ = _call(qa, base, "/api/run", {"ids": ["TC_X"], "who": "Somebody Else"})
    assert code == 200
    who, owner = started[-1]
    assert who == "QA One"                                   # not what the browser claimed
    assert owner == {"username": "qa1@qa.test", "mb_user": "qa1@mb", "mb_password": "pw-1"}


def test_a_qa_cannot_see_another_qas_run(srv, monkeypatch):
    base, _ = srv
    executor.JOBS["R-other"] = {"id": "R-other", "state": "running", "title": "", "total": 1, "done": 0, "steps": [],
                                "current": None, "results": [], "seconds": 0, "log": "secret",
                                "_owner": {"username": "boss@qa.test"}}
    try:
        qa = _client()
        _call(qa, base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"})
        assert _call(qa, base, "/api/run?id=R-other")[0] == 404
        ad = _client()
        _call(ad, base, "/api/auth/login", {"username": "boss@qa.test", "password": "password123"})
        assert _call(ad, base, "/api/run?id=R-other")[0] == 200
    finally:
        executor.JOBS.pop("R-other", None)


def test_record_is_refused_on_the_server_with_a_way_out(srv):
    base, _ = srv
    qa = _client()
    remote = {"X-Forwarded-For": "10.0.0.7"}                  # a QA on another PC, through the HTTPS proxy
    _call(qa, base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"}, remote)
    code, d, _ = _call(qa, base, "/api/record/start", {"url": "https://x"}, remote)
    assert code == 400 and "Use this code" in d["error"] and "--target=playwright-test" in d["error"]
    assert _call(qa, base, "/api/auth/state", None, remote)[1]["local"] is False


def test_record_works_directly_on_the_studio_pc(srv, monkeypatch):
    from ui_studio import recorder
    base, _ = srv
    monkeypatch.setattr(recorder, "start", lambda url, reuse=False, login_test=False: {"session": "s1", "command": "x"})
    admin = _client()
    _call(admin, base, "/api/auth/login", {"username": "boss@qa.test", "password": "password123"})
    assert _call(admin, base, "/api/auth/state")[1]["local"] is True       # the browser runs on the Studio's PC
    code, d, _ = _call(admin, base, "/api/record/start", {"url": "https://x"})
    assert code == 200 and d["session"] == "s1"


# ---------------------------------------------------------------- run queue

def test_slot_waits_for_same_login_and_same_company(monkeypatch):
    monkeypatch.setattr(mode, "MAX_BROWSERS", 3)
    a = {"_owner": {"mb_user": "u1"}}
    b = {"_owner": {"mb_user": "u1"}}
    c = {"_owner": {"mb_user": "u2"}}
    d = {"_owner": {"mb_user": "u3"}}
    co1 = {"steps": [{"action": "use_company", "value": "QA Grocery"}]}
    co2 = {"steps": [{"action": "use_company", "value": "QA Garment"}]}
    order = []

    def hold(job, case, tag, secs):
        with executor._slot(job, case):
            order.append(("in", tag))
            time.sleep(secs)
            order.append(("out", tag))

    t1 = threading.Thread(target=hold, args=(a, co1, "a", 2.0))       # long enough for a loaded machine
    t1.start()
    time.sleep(0.1)
    t2 = threading.Thread(target=hold, args=(b, co2, "b", 0.1))        # same MargBooks login as a: waits
    t3 = threading.Thread(target=hold, args=(c, co1, "c", 0.1))        # same company as a: waits
    t4 = threading.Thread(target=hold, args=(d, co2, "d", 0.1))        # free: runs now
    for t in (t2, t3, t4):
        t.start()
    time.sleep(0.3)
    assert b.get("waiting", "").startswith("your other run") and "qa grocery" in c.get("waiting", "")
    assert ("in", "d") in order and ("in", "b") not in order and ("in", "c") not in order
    for t in (t1, t2, t3, t4):
        t.join(10)
    assert order.index(("out", "a")) < order.index(("in", "b")) and order.index(("out", "a")) < order.index(("in", "c"))
    assert executor._busy["n"] == 0 and not executor._busy["mb"] and not executor._busy["co"]


def test_worker_protocol_round_trip(monkeypatch):
    """The run process's events reach the server's callbacks; its own console lines go to the log."""
    import io
    import subprocess

    lines = ["  [login] opening\n",
             '@@STUDIO@@ {"ev": "step", "ci": 0, "si": 0, "status": "ok", "secs": 1.2, "shot": "a.png"}\n',
             '@@STUDIO@@ {"ev": "log", "m": "Signed in"}\n',
             '@@STUDIO@@ {"ev": "result", "results": [{"outcome": "passed"}]}\n']

    class P:
        def __init__(self, *a, **k):
            self.env = k["env"]
            self.stdin = io.StringIO()
            self.stdout = iter(lines)
            self.returncode = 0

        def wait(self, timeout=None):
            return 0

    seen = {}
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: seen.setdefault("p", P(*a, **k)))
    steps, logs = [], []
    res = executor._play_isolated([{"id": "X", "steps": []}], {}, lambda *a: steps.append(a), logs.append,
                                  {"username": "qa1@qa.test", "mb_user": "qa1@mb", "mb_password": "pw"})
    assert res == [{"outcome": "passed"}]
    assert steps == [(0, 0, "ok", 1.2, "a.png")]
    assert logs == ["  [login] opening", "Signed in"]
    env = seen["p"].env
    assert env["STUDIO_RUN_CREDS"] == "1" and env["MARGBOOKS_USER"] == "qa1@mb" and env["USE_SAVED_SESSION"] == "false"


def test_run_process_keeps_its_own_margbooks_login(tmp_path, monkeypatch):
    """environments.json holds the shared login; a run process started for a QA must not take it."""
    from config import settings as S
    f = tmp_path / "environments.json"
    f.write_text(json.dumps({"active": "e", "envs": {"e": {"app_url": "https://a", "user": "shared@x",
                                                             "password": "shared-pw", "allow_writes": True}}}))
    monkeypatch.setenv("STUDIO_RUN_CREDS", "1")
    monkeypatch.setenv("MARGBOOKS_USER", "qa1@mb")
    monkeypatch.setenv("MARGBOOKS_PASS", "own-pw")
    old = (S.Settings.USER, S.Settings.PASSWORD, S.Settings.BASE_URL)
    try:
        S._apply_active_environment(f)
        assert (S.settings.USER, S.settings.PASSWORD, S.settings.BASE_URL) == ("qa1@mb", "own-pw", "https://a")
        monkeypatch.delenv("STUDIO_RUN_CREDS")
        S._apply_active_environment(f)
        assert (S.settings.USER, S.settings.PASSWORD) == ("shared@x", "shared-pw")
    finally:
        for k, v in zip(("USER", "PASSWORD", "BASE_URL"), old):
            setattr(S.Settings, k, v)
            setattr(S.settings, k, v)
