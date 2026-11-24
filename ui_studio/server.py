"""
Test Studio server (port 8778). Standard library only, like ui/server.py.

    python -m ui_studio.server        (or studio.bat)                 one tester, this PC (local mode)
    STUDIO_MODE=server python -m ui_studio.server  (studio-server.bat) the QA team, in the browser (see DEPLOY.md)

In server mode every page and call needs a Studio login (ui_studio.accounts), each QA's runs use their own
MargBooks login in a separate process, and settings that change the Studio for everybody are for admins only.

All logic is in the other ui_studio modules; this file only routes HTTP <-> JSON. The old UI (ui/server.py,
port 8777) keeps working unchanged and shares the same tests, environments and app memory.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from config.settings import ROOT, settings
from ui_studio import accounts, e2e, executor, feedback, team, grammar, learn, memory, mode, recorder, script, state, tests, verify

HERE = Path(__file__).resolve().parent
PORT = mode.PORT
TRADE_NAMES = {"auto": "Detect automatically"}
COOKIE = "ts_session"
MAX_BODY = 20 * 1024 * 1024
_req = threading.local()            # the Studio user of the request this thread is serving (server mode)


class Bad(Exception):
    """A request the tester can fix. Sent back as 400 with plain words."""


class Denied(Exception):
    """Logged in, but not allowed (403)."""


def me() -> dict | None:
    return getattr(_req, "user", None)


def _author(b: dict, key: str = "author") -> str:
    """Who did it: in server mode always the logged-in user (the browser cannot claim to be someone else)."""
    u = me()
    if mode.SERVER and u:
        return u["name"]
    return b.get(key, "") or ""


def _owner() -> dict | None:
    """Server mode: the logged-in QA and their own MargBooks login, for the run process."""
    if not mode.SERVER:
        return None
    u = me()
    creds = accounts.margbooks_login(u["username"]) if u else None
    if not creds:
        raise Bad("Add your own MargBooks login first: Settings > My MargBooks login. Runs use it, so two QAs "
                  "never log each other out.")
    return {"username": u["username"], "mb_user": creds[0], "mb_password": creds[1]}


def _admin(fn):
    """Server mode: only for admins (changes the Studio or the app for everybody)."""
    def wrapped(arg):
        if mode.SERVER and (me() or {}).get("role") != "admin":
            raise Denied("Only a Studio admin can do this.")
        return fn(arg)
    return wrapped


def _mine(job_id: str):
    if mode.SERVER and not executor.can_see(job_id, me()):
        raise KeyError("run not found")
    return job_id


def on_server_pc() -> bool:
    """The request comes from a browser on the Studio's own machine (its windows are on this person's screen)."""
    return bool(getattr(_req, "local", False))


def _no_record_on_server(b: dict):
    if mode.SERVER and not on_server_pc():
        raise Bad("Recording opens a browser window on the machine that runs the Studio, which you cannot see from "
                  "here. Record on your own PC (record.bat, or: python -m playwright codegen --target=playwright-test "
                  "<MargBooks URL>), copy ALL the code from the Playwright Inspector, paste it in “Recorded code” on "
                  "this screen and click “Use this code”.")
    return recorder.start(b.get("url", ""), bool(b.get("reuse_login")), bool(b.get("login_test")))


def _my_secrets() -> list[str]:
    """Server mode: the logged-in QA's own MargBooks password, so it is cleaned out of code they paste or save."""
    u = me()
    if not (mode.SERVER and u):
        return []
    try:
        creds = accounts.margbooks_login(u["username"])
    except Exception:  # noqa: BLE001
        creds = None
    return [creds[1]] if creds else []


def _my_users() -> list[str]:
    """Server mode: the logged-in QA's own MargBooks user id (a login test reads it from MB_USER)."""
    u = me()
    if not (mode.SERVER and u):
        return []
    try:
        creds = accounts.margbooks_login(u["username"])
    except Exception:  # noqa: BLE001
        creds = None
    return [creds[0]] if creds and creds[0] else []


def _str(b: dict, key: str, default: str = "") -> str:
    v = b.get(key, default)
    if v is None:
        return default
    if not isinstance(v, str):
        raise Bad(f"“{key}” must be text.")
    return v


# JSON body fields every POST endpoint reads as text, or as a list of text. A direct API caller that sends
# another type gets a plain 400 here, before any endpoint code calls .strip() on a number or a dict.
TEXT_FIELDS = frozenset({
    "id", "code", "src", "name", "module", "priority", "description", "source", "author", "who",
    "node", "text", "hash", "case", "session", "line", "screen", "term", "field", "web", "api", "job", "url",
    "user", "password", "old", "new", "username", "role", "login_url", "company",
    "kind", "place", "test", "run", "step", "error", "status", "reply", "q", "token", "new_email"})
TEXT_LIST_FIELDS = frozenset({"lines", "ids"})


def check_body_types(b: dict) -> dict:
    for k, v in b.items():
        if v is None:
            continue
        if k in TEXT_FIELDS and not isinstance(v, str):
            raise Bad(f"“{k}” must be text.")
        if k in TEXT_LIST_FIELDS and (not isinstance(v, list) or not all(isinstance(x, str) for x in v)):
            raise Bad(f"“{k}” must be a list of text.")
    return b


def _may_change_test(tid) -> None:
    """Server mode: a saved test is changed only by the QA who wrote it, or an admin (others save a copy)."""
    if not (mode.SERVER and tid):
        return
    owner = tests.owner_of(tid)
    u = me() or {}
    if owner is None or u.get("role") == "admin" or not owner or owner in (u.get("name"), u.get("username")):
        return
    raise Denied(f"{tid} was written by {owner}. Only {owner} or a Studio admin can change it. "
                 f"Click “+ New case” to write your own copy.")


def _is_admin() -> bool:
    return not mode.SERVER or (me() or {}).get("role") == "admin"


def feedback_add(b: dict) -> dict:
    """Any QA: send feedback. Who sent it is the logged-in user in team mode (the local Studio: the chosen name)."""
    u = me() if mode.SERVER else None
    return feedback.add(b, by_user=(u or {}).get("username", ""), by_name=_author(b, "who"),
                        extra_secrets=_my_secrets())


def feedback_list(q: dict) -> dict:
    """An admin (and the local Studio) sees all feedback; a QA in team mode sees their own."""
    mine = not _is_admin() or _q(q, "mine") == "1"
    viewer = ((me() or {}).get("username", "") if mode.SERVER else None) if mine else None
    if mine and not mode.SERVER:
        viewer = None
    out = feedback.list_feedback(viewer, _q(q, "status"), _q(q, "kind"), _q(q, "q"))
    out["admin"] = _is_admin()
    return out


def _who_key(b: dict) -> str:
    """Who did it, as the Team view keys people: the Studio username (team mode) or the chosen name (local)."""
    u = me()
    return (u or {}).get("username", "") if mode.SERVER and u else _author(b, "who")


def explain_ai(b: dict) -> dict:
    """AI explanation of a failure. With a run id it is stored with that run (asked once, the same for everyone)."""
    from ui_studio.explain import explain_ai as ask
    rid = _str(b, "run")
    if rid:
        r = tests.run_detail(rid)                       # KeyError (404) for an unknown run
        if (r.get("explain") or {}).get("ai"):
            return r["explain"]
        out = ask(r["run"]["err"] or _str(b, "error"), _str(b, "step"), f"{r['run']['test']} {r['run']['name']}")
        tests.store_ai_explain(rid, out)
        return out
    return ask(_str(b, "error"), _str(b, "step"), _str(b, "name"))


def feedback_update(b: dict) -> dict:
    return feedback.update(b.get("id"), b.get("status") or "", b.get("reply"), _author(b, "who"))


def save_test(b: dict) -> dict:
    tid = b.get("id") or None
    if tid is not None and not isinstance(tid, str):
        raise Bad("“id” must be text.")
    _may_change_test(tid)
    lines = b.get("lines")
    if lines is not None and (not isinstance(lines, list) or not all(isinstance(x, str) for x in lines)):
        raise Bad("“lines” must be a list of text lines.")
    return tests.save(_str(b, "code"), _str(b, "name"), _str(b, "module"), _str(b, "priority"),
                      _str(b, "description"), _author(b), _str(b, "source", "written"), lines, tid=tid,
                      extra_secrets=_my_secrets())


def save_draft(b: dict) -> dict:
    tid = b.get("id") or None
    if tid is not None and not isinstance(tid, str):
        raise Bad("“id” must be text.")
    _may_change_test(tid)
    return tests.save_draft(tid, _str(b, "name"), _str(b, "module"), _author(b), b.get("lines") or [])


def stop_run(b: dict) -> dict:
    rid = _str(b, "id")
    _mine(rid)
    return executor.stop_run(rid, (me() or {}).get("username", ""))


def admin_test_login(b=None) -> dict:
    """Settings > Test login with the shared environment login: waits, like a run, while a run uses the same
    MargBooks user (a second login of one user logs the first one out)."""
    env = _env()
    job = {"_owner": {"mb_user": env.get("user", ""), "username": (me() or {}).get("username", "")}, "title": ""}
    with executor._slot(job, {"steps": []}):
        return test_login()


# ------------------------------------------------------------------ accounts API

def auth_state(q=None) -> dict:
    return {"server": mode.SERVER, "user": me(), "needs_login": mode.SERVER and not me(),
            "local": on_server_pc()}            # Record opens its window on this screen: the direct Record button


def my_margbooks(b: dict) -> dict:
    u = me()
    if not u:
        raise Denied("Log in first.")
    try:
        accounts.set_margbooks_login(u["username"], b.get("user", ""), b.get("password") or None)
    except accounts.AuthError as e:
        raise Bad(str(e))
    return {"ok": True, "user": accounts.get_user(u["username"])}


def my_password(b: dict) -> dict:
    u = me()
    if not u:
        raise Denied("Log in first.")
    try:
        accounts.change_own_password(u["username"], b.get("old", ""), b.get("new", ""))
    except accounts.AuthError as e:
        raise Bad(str(e))
    return {"ok": True, "relogin": True}


def test_my_login(b=None) -> dict:
    """Server mode: sign in to MargBooks with the QA's own saved login (in a separate process)."""
    import os
    o = _owner()
    job = {"_owner": o, "title": ""}
    # a login while the same QA's run is going would log that run out: wait for it like a run does
    with executor._slot(job, {"steps": []}):
        return test_login(dict(os.environ, STUDIO_RUN_CREDS="1", MARGBOOKS_USER=o["mb_user"],
                               MARGBOOKS_PASS=o["mb_password"], USE_SAVED_SESSION="false", HEADLESS="true",
                               PYTHONIOENCODING="utf-8"))


def _invite_link(username: str) -> dict:
    token = accounts.create_invite(username)
    base = getattr(_req, "base", "") or f"http://127.0.0.1:{PORT}"
    return {"login_url": base + "/", "invite_url": f"{base}/#setpw={token}", "expires_hours": accounts.INVITE_HOURS}


def set_password_from_link(b: dict) -> dict:
    try:
        u = accounts.use_invite(_str(b, "token"), b.get("password") if isinstance(b.get("password"), str) else "")
    except accounts.AuthError as e:
        raise Bad(str(e))
    return {"ok": True, "email": u["username"]}


def users_save(b: dict) -> dict:
    """Admin: add a person (with a one-time "set your password" link to send them), give a new link, change role,
    name, e-mail, password or access."""
    try:
        if b.get("create"):
            u = accounts.create_user(b.get("username", ""), b.get("password", ""), b.get("role", "qa"),
                                     b.get("name", ""))
            return {"user": u, **_invite_link(u["username"]), "password_set": bool(b.get("password"))}
        if b.get("invite"):                                # a new "set your password" link (forgot / new device)
            return {"user": accounts.get_user(_str(b, "username")) or {}, **_invite_link(_str(b, "username"))}
        if b.get("new_email") is not None:                # admin gives an account a new login e-mail
            if not isinstance(b["new_email"], str):
                raise Bad("“new_email” must be text.")
            return {"user": accounts.change_email(b.get("username", ""), b["new_email"])}
        return {"user": accounts.update_user(b.get("username", ""), role=b.get("role"), name=b.get("name"),
                                             disabled=b.get("disabled"), password=b.get("password") or None)}
    except accounts.AuthError as e:
        raise Bad(str(e))


def _env() -> dict:
    from ui import envs
    return envs.apply_active() or {}


def users() -> list[str]:
    names = set()
    with state.db() as c:
        for t in ("tests", "runs"):
            names |= {r[0] for r in c.execute(f"SELECT DISTINCT author FROM {t} WHERE author<>''")}
    try:
        for t in tests.list_tests():
            if t["author"] and t["author"] != "unknown":
                names.add(t["author"])
    except Exception:  # noqa: BLE001
        pass
    return sorted(names)


def get_state() -> dict:
    from framework import ai as ai_mod
    env, s = _env(), state.load_settings()
    ts, rn = tests.list_tests(), tests.list_runs()
    passed = rn["kpis"]["passed"]
    av = ai_mod.available()
    return {"env": {"name": env.get("name", ""), "app_url": env.get("app_url", ""), "login_url": env.get("login_url", ""), "company": env.get("company", ""),
                    "user": env.get("user", "")},
            "trade": memory.build()["trade"], "modules": state.MODULES + sorted(
                {t["module"] for t in ts} - set(state.MODULES)), "users": users(),
            "ai": {"provider": av.get("active") or "", "active": bool(av.get("active")), "mode": s["ai_mode"],
                   "limit": s["token_limit"], "used": state.tokens_used()},
            "memory": memory.stats(),
            "kpis": {"tests": len(ts), "testers": len({t["author"] for t in ts if t["author"] != "unknown"}),
                     "runs": rn["kpis"]["runs"],
                     "pass_rate": round(passed / rn["kpis"]["runs"] * 100) if rn["kpis"]["runs"] else None},
            "allow_writes": bool(env.get("allow_writes")),
            "server": mode.SERVER, "me": me() if mode.SERVER else None,
            "feedback_open": feedback.open_count() if _is_admin() else 0}


def get_settings() -> dict:
    env, s = _env(), state.load_settings()
    trade = memory.build()["trade"]
    return {"url": env.get("app_url", ""), "login_url": env.get("login_url", ""), "user": env.get("user", ""),
            "has_password": bool(env.get("password")), "company": env.get("company", ""),
            "trade_mode": s["trade_mode"],
            "trade_options": [{"value": "auto", "label": "Detect automatically" + (f" (now: {trade})" if trade else "")}]
            + [{"value": t, "label": t} for t in state.TRADES],
            "bulk": s["bulk"], "codegen_cmd": s["codegen_cmd"], "out_dir": s["out_dir"], "ai_mode": s["ai_mode"],
            "token_limit": s["token_limit"], "fix_attempts": s["fix_attempts"],
            "allow_writes": bool(env.get("allow_writes")), "test_company": s["test_company"],
            "web_dir": s["web_dir"], "api_dir": s["api_dir"]}


def post_settings(b: dict) -> dict:
    from ui import envs
    env = envs.apply_active() or {}
    if not env.get("name"):
        raise Bad("No environment is set up yet.")
    url = (b.get("url") or env.get("app_url") or "").strip().rstrip("/")
    if not url:
        raise Bad("URL is required.")
    try:
        envs.upsert({"name": env["name"], "app_url": url, "login_url": (b.get("login_url") or url + "/login"),
                     "user": b.get("user", env.get("user", "")), "password": b.get("password") or "",
                     "company": b.get("company", env.get("company", "")),
                     "allow_writes": bool(b.get("allow_writes", env.get("allow_writes")))})
        envs.apply_active()
        state.save_settings({k: b[k] for k in state.DEFAULTS if k in b})
    except ValueError as e:
        raise Bad(str(e))
    return {"ok": True}


def test_login(env: dict | None = None) -> dict:
    try:
        boot = "import sys,runpy;sys.path.insert(0,sys.argv[1]);runpy.run_module('framework.auth',run_name='__main__')"
        p = subprocess.run([sys.executable, "-c", boot, str(ROOT)], cwd=str(ROOT), capture_output=True, text=True,
                           timeout=150, encoding="utf-8", errors="replace", env=env)
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "Login took longer than 150 seconds."}
    text = p.stdout + p.stderr
    if "LOGIN + COMPANY SELECT SUCCESS" in text and p.returncode == 0:
        landed = next((l.strip() for l in reversed(text.splitlines()) if l.strip().startswith("http")), "")
        return {"ok": True, "message": "Login worked." + (f" Landed on {landed}" if landed else "")}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if "*** FAIL ***" in text:
        i = max(k for k, l in enumerate(lines) if "FAIL" in l)
        msg = " ".join(lines[i + 1:i + 3])
    else:
        msg = lines[-1] if lines else "Login did not finish."
    if "anjaan screen" in msg.lower() and "accounts.margbooks.com" in msg:
        msg = ("MargBooks stayed on the Sign In page after the User ID was typed. Usually MargBooks does not "
               "recognise the User ID (check the email or mobile number in Settings). Screenshot: " + msg.split("artifacts/")[-1])
    return {"ok": False, "message": msg[:400]}


def ai_suggest(line: str, screen: str) -> dict:
    """AI for ONE red line: only the line and the field names of the current screen are sent."""
    M = grammar.Memory()
    names = [f["name"] for f in (M.screens.get(screen) or {}).get("fields", [])]
    s = state.load_settings()
    if s["ai_mode"] == "never":
        return {"ok": False, "msg": "AI is switched off in Settings."}
    # The AI gets the grammar, the screens app memory knows and the fields of the current screen, and may
    # split one free-text line ("Deposit cash in bank: Cr cash, Dr bank, same amount; saves") into steps.
    try:
        ans, tok, cached = state.ai_json(
            "write.lines",
            "Turn one free-text test step into 1-6 steps of this grammar, one step per string:\n"
            "Log in | Open <screen> | Select party \"x\" | Select item \"x\" with qty \"n\", rate \"n\" | "
            "Enter \"value\" in <field> | Set <field> to <value> | Click <button> | Save bill | "
            "Verify \"text on screen\" | Wait <n> seconds.\n"
            "Use only screen names from the screens list and field names from the fields list. "
            "If the step needs a screen or field that is not in those lists, put its name in \"missing\".\n"
            "Reply JSON {\"lines\": [\"...\"], \"missing\": \"\"}. Use {\"lines\": []} when unsure.",
            f"screens: {sorted(M.screens)}\ncurrent screen: {screen or 'none yet'}\nfields: {names}\nstep: {line}", 400)
    except state.AIBlocked as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": "AI could not be reached: " + str(e)[:120]}
    ans = ans or {}
    lines = [str(x).strip() for x in (ans.get("lines") or ([ans["line"]] if ans.get("line") else [])) if str(x).strip()][:6]
    missing = str(ans.get("missing") or "").strip()
    if missing:
        return {"ok": False, "tokens": tok, "msg": f"The agent has not learned “{missing}” yet, so this step cannot be "
                f"automated. Open Learn app and learn that screen, then check this line again."}
    if not lines:
        return {"ok": False, "tokens": tok, "msg": "AI could not map this line confidently. Split it into short steps, "
                "e.g. “Open Payment” / “Set Amount to 500” / “Click Save”."}
    start = [f"Open {screen}"] if screen else []
    results, _ = grammar.parse_all(start + lines, M)
    bad = [ln for ln, r in zip(lines, results[len(start):]) if r["status"] != "ok"]
    if bad:
        return {"ok": False, "tokens": tok, "msg": f"AI suggested “{' / '.join(lines)}”, but “{bad[0]}” does not match "
                f"app memory, so it was not used."}
    return {"ok": True, "rewrite": "\n".join(lines), "tokens": tok, "cached": cached}


def download(kind: str, ident: str) -> tuple[bytes, str, str]:
    """(bytes, filename, content type)"""
    if kind == "bugpack":
        return tests.bug_pack(ident), f"{ident}-bugpack.zip", "application/zip"
    if kind == "report":
        return tests.report_html(ident).encode("utf-8"), f"{ident}-report.html", "text/html; charset=utf-8"
    if kind == "trace":                     # scrubbed: a trace never carries a MargBooks password
        return tests.trace_bytes(ident), f"{ident}-trace.zip", "application/zip"
    if kind == "video":
        return tests.run_file(ident, "run.webm").read_bytes(), f"{ident}-run.webm", "video/webm"
    if kind == "spec":
        return tests.spec_text(ident).encode("utf-8"), f"{ident}.spec.ts", "text/plain; charset=utf-8"
    if kind == "recorder":
        return tests.recorder_for_test(ident).encode("utf-8"), f"{ident}-recorder.json", "application/json"
    raise Bad("Unknown download kind.")


def _q(q, k, d=""):
    return (q.get(k) or [d])[0]


GET = {
    "/api/state": lambda q: get_state(),
    "/api/settings": _admin(lambda q: get_settings()),
    "/api/memory": lambda q: memory.rows(_q(q, "screen"), _q(q, "q")),
    "/api/learn/status": lambda q: learn.status(_q(q, "job"), int(_q(q, "since", "0") or 0)),
    "/api/record/feed": lambda q: recorder.feed(_q(q, "session"), int(_q(q, "since", "0") or 0)),
    "/api/replay/status": lambda q: executor.replay_status(_mine(_q(q, "job"))),
    "/api/tests": lambda q: {"tests": tests.list_tests()},
    "/api/tests/open": lambda q: tests.open_test(_q(q, "id")),
    "/api/tests/case": lambda q: tests.case_detail(_q(q, "id")),
    "/api/scripts": lambda q: {"scripts": e2e.list_scripts(tests.module_yaml(_q(q, "module"))),
                               "problem": e2e.setup_problem()},
    "/api/scripts/detail": lambda q: e2e.script_detail(_q(q, "node")),
    "/api/scripts/status": lambda q: e2e.status(_q(q, "job")),
    "/api/scripts/current": lambda q: e2e.current(),
    "/api/scripts/new/status": lambda q: e2e.new_script_status(_q(q, "job")),
    "/api/scripts/source": lambda q: e2e.source(_q(q, "node")),
    "/api/run": lambda q: executor.run_status(_mine(_q(q, "id"))),
    "/api/run/mine": lambda q: {"runs": executor.live_runs(me() if mode.SERVER else None)},
    "/api/runs": lambda q: tests.list_runs(),
    "/api/runs/detail": lambda q: tests.run_detail(_q(q, "id")),
    "/api/tokens": lambda q: state.tokens_report(),
    "/api/auth/state": auth_state,
    "/api/queue": lambda q: executor.queue(),
    "/api/users": _admin(lambda q: {"users": [u | {"invite_open": u["username"] in pend}
                                              for pend in [accounts.pending_invites()] for u in accounts.list_users()]}),
    "/api/feedback": feedback_list,
    "/api/feedback/known": lambda q: {"known": feedback.known_issues()},
    "/api/team": _admin(lambda q: team.overview(_q(q, "days", "7"))),
}
PUBLIC = {"/", "/index.html", "/favicon.ico", "/healthz", "/api/auth/state", "/api/auth/login",
          "/api/auth/invite", "/api/auth/setpw"}            # the "set your password" link works before a login


POST = {
    "/api/settings": post_settings,
    "/api/settings/test-login": admin_test_login,
    "/api/learn/start": lambda b: learn.start(),
    "/api/learn/restore": lambda b: learn.restore(),
    "/api/code/read": lambda b: learn.read_code(b.get("web", ""), b.get("api", "")),
    "/api/write/check": lambda b: grammar.check(b.get("lines") or []),
    "/api/write/ai": lambda b: ai_suggest(b.get("line", ""), b.get("screen", "")),
    "/api/write/teach": lambda b: (memory.teach(b.get("term", ""), b.get("screen", ""), b.get("field", "")), {"ok": True})[1],
    "/api/write/untaught": lambda b: {"ok": memory.untaught(b.get("term", ""), b.get("screen", ""))},
    "/api/write/generate": lambda b: script.generate(b.get("name", ""), b.get("module", ""), _author(b),
                                                      b.get("lines") or []),
    "/api/record/start": _no_record_on_server,
    "/api/record/stop": lambda b: recorder.stop(b.get("session", "")),
    "/api/record/paste": lambda b: recorder.paste(b.get("code", ""), _my_secrets(), b.get("login_test") is True,
                                                  _my_users()),
    "/api/verify": lambda b: verify.run(b.get("code", ""), b.get("src", "record")),
    "/api/verify/apply": lambda b: {"code": verify.apply(b.get("code", ""), b.get("ids") or [])},
    "/api/replay": lambda b: {"job": executor.start_replay(b.get("code", ""), b.get("name", ""), b.get("module", ""),
                                                           _author(b), owner=_owner())},
    "/api/replay/retry": lambda b: {"job": executor.retry(_mine(b.get("job", "")))},
    "/api/save": save_test,
    "/api/tests/save-draft": save_draft,
    "/api/scripts/run": lambda b: e2e.start(b.get("node", ""), bool(b.get("headed")), owner=_owner(),
                                            who=_author(b, "who")),
    "/api/scripts/save": lambda b: e2e.save(b.get("node", ""), b.get("text", ""), b.get("hash", "")),
    "/api/scripts/new": lambda b: e2e.new_script_start(b.get("case", ""), _who_key(b)),
    "/api/run": lambda b: {"run_id": executor.start_run(b.get("ids") or [], {
        "video": b.get("video", True), "shots": b.get("shots", True), "bugpack": b.get("bugpack", True),
        "stop_first": b.get("stop_first", False)}, _author(b, "who"), owner=_owner())},
    "/api/run/stop": stop_run,
    # accounts
    "/api/me/margbooks": my_margbooks,
    "/api/auth/invite": lambda b: {"email": accounts.invite_user(_str(b, "token")) or ""},
    "/api/auth/setpw": set_password_from_link,
    "/api/me/password": my_password,
    "/api/me/margbooks/test": test_my_login,
    "/api/users": _admin(users_save),
    "/api/feedback": feedback_add,
    "/api/feedback/update": _admin(feedback_update),
    "/api/explain/ai": explain_ai,
}
# Changes the Studio, the shared environment or the app for everybody: admins only (server mode).
for _k in ("/api/settings", "/api/settings/test-login", "/api/learn/start", "/api/learn/restore", "/api/code/read",
           "/api/scripts/save", "/api/scripts/new", "/api/scripts/run", "/api/write/untaught"):
    POST[_k] = _admin(POST[_k])



class _HeaderWatch:
    """One watchdog thread for all connections: a handler still reading its request line and headers after its
    deadline gets its socket shut down (which ends the blocked read)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._due: dict = {}          # handler -> deadline (monotonic)
        self._expired: set = set()    # id() of handlers whose deadline passed
        self._thread = None

    def start(self, h, seconds: float) -> None:
        import time
        with self._lock:
            self._expired.discard(id(h))
            self._due[h] = time.monotonic() + seconds
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._loop, name="header-watch", daemon=True)
                self._thread.start()

    def done(self, h) -> bool:
        """Stop watching h. True when its deadline had already passed (its socket was shut down)."""
        with self._lock:
            self._due.pop(h, None)
            if id(h) in self._expired:
                self._expired.discard(id(h))
                return True
            return False

    def _loop(self) -> None:
        import time
        while True:
            time.sleep(0.5)
            now = time.monotonic()
            with self._lock:
                late = [h for h, t in self._due.items() if t <= now]
                for h in late:
                    del self._due[h]
                    self._expired.add(id(h))
            for h in late:
                try:
                    h._header_timeout()
                except Exception:  # noqa: BLE001
                    pass


_header_watch = _HeaderWatch()


class Handler(BaseHTTPRequestHandler):
    server_version = "TestStudio"
    sys_version = ""
    # A client that stops sending (half a request line or headers, or a body shorter than its Content-Length) is
    # dropped: without a socket timeout each such connection held a handler thread (and its body buffer) for ever,
    # and anyone on the network could open many of them without logging in.
    timeout = 60
    BODY_SECONDS = 120   # the whole request body must arrive within this time (a trickle of bytes is dropped too)
    # The request line and all headers must arrive within this time from their first byte. `timeout` is per
    # recv, so without it a client sending one header byte every 30 s held a handler thread for days (slowloris).
    HEADER_SECONDS = 30

    def log_message(self, *a):
        pass

    def handle_one_request(self):
        try:
            first = self.rfile.peek(1)          # waiting for a request on a kept-alive connection: `timeout` applies
        except (TimeoutError, OSError):
            self.close_connection = True
            return
        if not first:
            self.close_connection = True
            return
        _header_watch.start(self, self.HEADER_SECONDS)
        try:
            super().handle_one_request()
        except OSError:
            if not _header_watch.done(self):
                raise
            self.close_connection = True    # cut off at the header deadline (Windows: the read raises, not b"")
        finally:
            _header_watch.done(self)

    def parse_request(self):
        self._t0 = __import__("time").monotonic()     # the access log says how long each request took
        ok = super().parse_request()
        if _header_watch.done(self):                  # the headers were cut off at the deadline: no reply
            self.close_connection = True
            return False
        return ok

    def _header_timeout(self):
        """Called by the header watchdog: the client did not finish its request line and headers in time."""
        import socket
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def _send(self, code: int, body, ctype="application/json", extra: dict | None = None):
        data = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        if mode.SECURE_COOKIE:
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        extra = dict(extra or {})
        slide = getattr(self, "_slide", None)
        if slide and "Set-Cookie" not in extra:     # the session moved on: so does the cookie (12 h of inactivity)
            extra.update(self._cookie(slide, accounts.SESSION_HOURS * 3600))
        self._slide = None
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        _access_log(self, code)

    def send_error(self, code, message=None, explain=None):
        """Errors the standard library sends itself (bad request line, unknown method): JSON with the same
        security headers, and in the access log."""
        try:
            self.close_connection = True
            self._json({"error": message or self.responses.get(code, ("Error",))[0]}, code)
        except Exception:  # noqa: BLE001
            pass

    def _no_method(self):
        self._json({"error": "Method not allowed."}, 405)

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_TRACE = do_CONNECT = _no_method

    def do_HEAD(self):
        """Monitoring tools that check with HEAD: /healthz answers; everything else is 405."""
        if urlparse(self.path).path == "/healthz":
            return self._json(self._health())
        return self._no_method()

    @staticmethod
    def _health() -> dict:
        """Public, so only counts: no usernames, no test names."""
        q = executor.queue()
        jobs = q.get("jobs") or []
        return {"ok": True, "mode": "server" if mode.SERVER else "local", "max_browsers": q.get("max_browsers"),
                "busy": q.get("busy"), "running": sum(1 for j in jobs if not j.get("waiting")),
                "waiting": sum(1 for j in jobs if j.get("waiting"))}

    # ---------- server mode: who is asking ----------
    def _token(self) -> str | None:
        from http.cookies import SimpleCookie
        try:
            c = SimpleCookie(self.headers.get("Cookie") or "")
            return c[COOKIE].value if COOKIE in c else None
        except Exception:  # noqa: BLE001
            return None

    def _who(self, path: str) -> bool:
        """Sets the request's user. False (and a reply already sent) when a login is needed."""
        _req.user = None
        self._slide = None
        # the browser runs on the machine that runs the Studio (not through a proxy): a recording window opened
        # here is on this person's own screen, so Record works directly also in team mode
        _req.local = self.client_address[0] in ("127.0.0.1", "::1") and not self.headers.get("X-Forwarded-For")
        proto = (self.headers.get("X-Forwarded-Proto") or ("https" if mode.SECURE_COOKIE else "http")).split(",")[0]
        host = (self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or f"127.0.0.1:{PORT}").split(",")[0]
        _req.base = f"{proto.strip()}://{host.strip()}"         # the address people open: for "set password" links
        if not mode.SERVER:
            return True
        info: dict = {}
        tok = self._token()
        _req.user = accounts.session_user(tok, info)
        if _req.user and info.get("slid"):
            self._slide = tok
        if _req.user or path in PUBLIC:
            return True
        self._json({"error": "Please log in.", "login": True}, 401)
        return False

    def _same_site(self) -> bool:
        """POSTs come only from the Studio page itself (CSRF): its own header, and the same origin."""
        if not mode.SERVER:
            return True
        if self.headers.get("X-Studio") != "1":
            return False
        origin = self.headers.get("Origin")
        if origin:
            host = (self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "").split(",")[0].strip()
            return urlparse(origin).netloc == host
        return True

    def _cookie(self, token: str, max_age: int) -> dict:
        v = f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}"
        if mode.SECURE_COOKIE:
            v += "; Secure"
        return {"Set-Cookie": v}

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str))

    def _call(self, fn, arg):
        try:
            self._json(fn(arg))
        except Bad as e:
            self._json({"error": str(e)}, 400)
        except Denied as e:
            self._json({"error": str(e)}, 403)
        except (ValueError, state.AIBlocked) as e:
            self._json({"error": str(e)}, 400)
        except KeyError as e:
            self._json({"error": str(e.args[0]) if e.args else "not found"}, 404)
        except Exception:  # noqa: BLE001  (details go to the server log only: exception text can hold a server path)
            ref = __import__("secrets").token_hex(4)
            sys.stderr.write(f"[error {ref}] {self.command} {urlparse(self.path).path}\n" + traceback.format_exc())
            self._json({"error": f"Something went wrong inside Test Studio (error {ref}). Try again; if it keeps "
                                 f"happening, tell the Studio admin (the details are in the server log under {ref})."}, 500)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/healthz":
            return self._json(self._health())
        if not self._who(u.path):
            return
        if u.path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        if u.path in ("/", "/index.html"):
            return self._send(200, (HERE / "app.html").read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/download":
            try:
                data, name, ctype = download(_q(q, "kind"), _q(q, "id"))
                return self._send(200, data, ctype, {"Content-Disposition": f'attachment; filename="{quote(name)}"'})
            except Bad as e:
                return self._json({"error": str(e)}, 400)
            except KeyError as e:
                msg = str(e.args[0]) if e.args else ""
                return self._json({"error": msg if msg.startswith("That ") else "That file does not exist for this run."}, 404)
            except FileNotFoundError:
                return self._json({"error": "That file does not exist for this run."}, 404)
            except Exception:  # noqa: BLE001  (details go to the server log, never a server path to the browser)
                sys.stderr.write(traceback.format_exc())
                return self._json({"error": "The download could not be prepared. Try again in a minute; if it "
                                            "keeps failing, tell the Studio admin (details are in the server log)."}, 500)
        if u.path == "/api/run/shot":
            try:
                return self._send(200, executor.run_shot(_mine(_q(q, "id"))).read_bytes(), "image/png")
            except Exception:  # noqa: BLE001
                return self._send(404, "not found", "text/plain")
        if u.path == "/api/verify/shot":
            try:
                return self._send(200, tests.verify_shot(_q(q, "name")).read_bytes(), "image/png")
            except Exception:  # noqa: BLE001
                return self._send(404, "not found", "text/plain")
        if u.path == "/api/runs/file":
            try:
                p = tests.run_shot_file(_q(q, "id"), _q(q, "name"))      # step screenshots only
                return self._send(200, p.read_bytes(), "image/png")
            except Exception:  # noqa: BLE001
                return self._send(404, "not found", "text/plain")
        if u.path == "/api/scripts/shot":                              # a running script's step screenshot
            try:
                return self._send(200, e2e.shot_file(_q(q, "job"), _q(q, "name")).read_bytes(), "image/png")
            except Exception:  # noqa: BLE001
                return self._send(404, "not found", "text/plain")
        if u.path == "/api/tests":
            return self._tests_list()
        fn = GET.get(u.path)
        if not fn:
            return self._json({"error": "not found"}, 404)
        self._call(fn, q)

    def _tests_list(self):
        """/api/tests: the list's JSON is encoded (and gzipped) once per list, not on every request of the team."""
        try:
            raw, gz = tests.list_tests_body()
        except Exception:  # noqa: BLE001
            return self._call(GET["/api/tests"], {})
        if gz and "gzip" in (self.headers.get("Accept-Encoding") or "").lower():
            return self._send(200, gz, extra={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
        return self._send(200, raw, extra={"Vary": "Accept-Encoding"})

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._same_site():
            return self._json({"error": "Request refused (not from the Test Studio page)."}, 403)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0:
            self.close_connection = True
            return self._json({"error": "Bad Content-Length."}, 400)
        if n > MAX_BODY:
            self._drain(n)
            self.close_connection = True
            return self._json({"error": "Request too large (the limit is 20 MB)."}, 413)
        if path not in ("/api/auth/login", "/api/auth/logout") and not self._who(path):
            self.close_connection = True          # the body was not read: only a logged-in user's body is
            return
        raw = self._read_body(n)
        if raw is None:                           # the client stopped sending: drop it
            self.close_connection = True
            return
        try:
            body = json.loads(raw or b"{}") if n else {}
        except ValueError:
            return self._json({"error": "Request was not valid JSON."}, 400)
        if not isinstance(body, dict):
            return self._json({"error": "Request must be a JSON object."}, 400)
        if path == "/api/auth/login":
            return self._login(body)
        if path == "/api/auth/logout":
            accounts.logout(self._token())
            return self._send(200, json.dumps({"ok": True}), extra=self._cookie("", 0))
        fn = POST.get(path)
        if not fn:
            return self._json({"error": "not found"}, 404)
        self._call(lambda b: fn(check_body_types(b)), body)

    def _read_body(self, n: int) -> bytes | None:
        """The request body, or None when the client does not send all of it within BODY_SECONDS."""
        import time as _t
        if not n:
            return b""
        end = _t.time() + self.BODY_SECONDS
        parts, left = [], n
        try:
            while left > 0:
                if _t.time() > end:
                    return None
                chunk = self.rfile.read1(min(left, 1 << 20)) if hasattr(self.rfile, "read1") else self.rfile.read(min(left, 1 << 16))
                if not chunk:
                    return None
                parts.append(chunk)
                left -= len(chunk)
        except (TimeoutError, OSError):
            return None
        return b"".join(parts)

    def _drain(self, n: int, limit: int = 4 * MAX_BODY):
        """Read (and drop) a refused body, so the browser gets the 413 reply instead of a reset connection."""
        left = min(n, limit)
        try:
            self.connection.settimeout(15)
            while left > 0:
                chunk = self.rfile.read(min(left, 1 << 20))
                if not chunk:
                    break
                left -= len(chunk)
        except Exception:  # noqa: BLE001
            pass

    def _login(self, b: dict):
        if not mode.SERVER:
            return self._json({"ok": True, "user": None})
        try:
            token, user = accounts.login(b.get("username", ""), b.get("password", ""))
        except accounts.AuthError as e:
            return self._json({"error": str(e)}, 401)
        except Exception:  # noqa: BLE001
            sys.stderr.write(traceback.format_exc())
            return self._json({"error": "Wrong username or password."}, 401)
        self._send(200, json.dumps({"ok": True, "user": user}), extra=self._cookie(token, accounts.SESSION_HOURS * 3600))


_log_lock = threading.Lock()


def _elapsed_ms(h) -> str:
    t0 = getattr(h, "_t0", None)
    return f"{int((__import__('time').monotonic() - t0) * 1000)}ms" if t0 is not None else "-"


def _access_log(h, code: int):
    """logs/studio_access.log: time, user, method, path (no query: it can hold ids only, but keep it short)."""
    if not mode.SERVER:
        return
    try:
        line = (f"{__import__('time').strftime('%Y-%m-%d %H:%M:%S')}\t{h.client_address[0]}\t"
                f"{(me() or {}).get('username', '-')}\t{h.command}\t{urlparse(h.path).path}\t{code}\t"
                f"{_elapsed_ms(h)}\n")
        f = ROOT / "logs" / "studio_access.log"
        with _log_lock:
            f.parent.mkdir(exist_ok=True)
            if f.exists() and f.stat().st_size > 20 * 1024 * 1024:
                f.replace(f.with_suffix(".log.1"))
            with f.open("a", encoding="utf-8") as fh:
                fh.write(line)
    except Exception:  # noqa: BLE001
        pass


def _cleanup_old_runs():
    """Server mode: run folders (screenshots, video, trace) older than STUDIO_KEEP_RUN_DAYS are deleted daily."""
    import time as _t
    while True:
        try:
            cleanup_old_runs_once()
        except Exception:  # noqa: BLE001
            pass
        _t.sleep(86400)


def cleanup_old_runs_once(root: Path | None = None, days: int | None = None) -> list[str]:
    """Delete run folders older than `days` (STUDIO_KEEP_RUN_DAYS). 0 or less: keep everything. Never a folder
    younger than a day, and never the folder of a run or replay that is still going. Returns what was deleted."""
    import shutil
    import time as _t
    days = mode.KEEP_RUN_DAYS if days is None else days
    if days <= 0:
        return []
    root = root or executor.RUNS_DIR
    cut = min(_t.time() - days * 86400, _t.time() - 86400)
    live = {Path(j["dir"]).resolve() for j in list(executor.JOBS.values())
            if j.get("dir") and j.get("state") in ("queued", "running", "fixing")}
    gone = []
    for d in Path(root).glob("*"):
        try:
            if d.is_dir() and d.stat().st_mtime < cut and d.resolve() not in live:
                shutil.rmtree(d, ignore_errors=True)
                gone.append(d.name)
        except OSError:
            pass
    return gone


def _quiet(fn):
    try:
        fn()
    except Exception:  # noqa: BLE001
        pass


def main():
    from ui import envs
    envs.apply_active()
    try:
        settings.validate()
    except RuntimeError as e:      # a new PC has no .env yet; the Settings screen is where it is filled in
        print("\n  Note: login details are not set yet (" + str(e).splitlines()[0] + ").")
        print("  Open Settings in the UI and fill them in.")
    # Warm the test list in the background: the first parse of 3,000+ cases takes seconds.
    threading.Thread(target=lambda: _quiet(tests.list_tests), daemon=True).start()
    if mode.SERVER:
        if not any(u["role"] == "admin" and not u["disabled"] for u in accounts.list_users()):
            print("\n  No Studio admin yet. Make one first:\n    python -m ui_studio.accounts add <username> --admin\n")
            sys.exit(2)
        threading.Thread(target=_cleanup_old_runs, daemon=True).start()
    srv = ThreadingHTTPServer((mode.HOST, PORT), Handler)
    srv.daemon_threads = True
    url = f"http://{'localhost' if mode.HOST in ('127.0.0.1', '0.0.0.0') else mode.HOST}:{PORT}"
    kind = "server mode (team, login required)" if mode.SERVER else "local mode (this PC only)"
    print(f"\n{'=' * 52}\n  MargBooks Test Studio is running, {kind}\n  {url}\n  Press Ctrl+C to stop\n{'=' * 52}\n")
    if not mode.SERVER:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
