"""
Test Studio server (port 8778). Standard library only, like ui/server.py.

    python -m ui_studio.server        (or studio.bat)

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
from ui_studio import executor, grammar, learn, memory, recorder, script, state, tests, verify

HERE = Path(__file__).resolve().parent
PORT = 8778
TRADE_NAMES = {"auto": "Detect automatically"}


class Bad(Exception):
    """A request the tester can fix. Sent back as 400 with plain words."""


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
            "allow_writes": bool(env.get("allow_writes"))}


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


def test_login() -> dict:
    try:
        boot = "import sys,runpy;sys.path.insert(0,sys.argv[1]);runpy.run_module('framework.auth',run_name='__main__')"
        p = subprocess.run([sys.executable, "-c", boot, str(ROOT)], cwd=str(ROOT), capture_output=True, text=True,
                           timeout=150, encoding="utf-8", errors="replace")
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
    try:
        ans, tok, cached = state.ai_json(
            "write.line", "Rewrite one test step in the tester's grammar. Allowed forms: Open <screen>; "
            "Select party \"x\"; Enter <n> in <field>; Set <field> to <n>; Click <button>. "
            "Reply JSON {\"line\":\"<rewritten step>\"} or {\"line\":\"\"} when unsure.",
            f"screen: {screen or 'unknown'}\nfields: {names}\nstep: {line}", 200)
    except state.AIBlocked as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": "AI could not be reached: " + str(e)[:120]}
    rewrite = str((ans or {}).get("line", "")).strip()
    if not rewrite:
        return {"ok": False, "tokens": tok, "msg": "AI could not map this line confidently. Write it shorter, e.g. “Set Rate to 50”."}
    check = grammar.parse(rewrite, {"screen": screen or None}, M)
    if check["status"] != "ok":
        return {"ok": False, "tokens": tok, "msg": f"AI suggested “{rewrite}”, but it does not match app memory, so it was rejected."}
    return {"ok": True, "rewrite": rewrite, "tokens": tok, "cached": cached}


def download(kind: str, ident: str) -> tuple[bytes, str, str]:
    """(bytes, filename, content type)"""
    if kind == "bugpack":
        return tests.bug_pack(ident), f"{ident}-bugpack.zip", "application/zip"
    if kind == "report":
        return tests.report_html(ident).encode("utf-8"), f"{ident}-report.html", "text/html; charset=utf-8"
    if kind in ("trace", "video"):
        name = "trace.zip" if kind == "trace" else "run.webm"
        p = tests.run_file(ident, name)
        return p.read_bytes(), f"{ident}-{name}", "application/zip" if kind == "trace" else "video/webm"
    if kind == "spec":
        return tests.spec_text(ident).encode("utf-8"), f"{ident}.spec.ts", "text/plain; charset=utf-8"
    if kind == "recorder":
        return tests.recorder_for_test(ident).encode("utf-8"), f"{ident}-recorder.json", "application/json"
    raise Bad("Unknown download kind.")


def _q(q, k, d=""):
    return (q.get(k) or [d])[0]


GET = {
    "/api/state": lambda q: get_state(),
    "/api/settings": lambda q: get_settings(),
    "/api/memory": lambda q: memory.rows(_q(q, "screen"), _q(q, "q")),
    "/api/learn/status": lambda q: learn.status(_q(q, "job"), int(_q(q, "since", "0") or 0)),
    "/api/record/feed": lambda q: recorder.feed(_q(q, "session"), int(_q(q, "since", "0") or 0)),
    "/api/replay/status": lambda q: executor.replay_status(_q(q, "job")),
    "/api/tests": lambda q: {"tests": tests.list_tests()},
    "/api/tests/open": lambda q: tests.open_test(_q(q, "id")),
    "/api/run": lambda q: executor.run_status(_q(q, "id")),
    "/api/runs": lambda q: tests.list_runs(),
    "/api/runs/detail": lambda q: tests.run_detail(_q(q, "id")),
    "/api/tokens": lambda q: state.tokens_report(),
}

POST = {
    "/api/settings": post_settings,
    "/api/settings/test-login": lambda b: test_login(),
    "/api/learn/start": lambda b: learn.start(),
    "/api/learn/restore": lambda b: learn.restore(),
    "/api/code/read": lambda b: learn.read_code(b.get("web", ""), b.get("api", "")),
    "/api/write/check": lambda b: grammar.check(b.get("lines") or []),
    "/api/write/ai": lambda b: ai_suggest(b.get("line", ""), b.get("screen", "")),
    "/api/write/teach": lambda b: (memory.teach(b.get("term", ""), b.get("screen", ""), b.get("field", "")), {"ok": True})[1],
    "/api/write/generate": lambda b: script.generate(b.get("name", ""), b.get("module", ""), b.get("author", ""),
                                                      b.get("lines") or []),
    "/api/record/start": lambda b: recorder.start(b.get("url", ""), bool(b.get("reuse_login"))),
    "/api/record/stop": lambda b: recorder.stop(b.get("session", "")),
    "/api/verify": lambda b: verify.run(b.get("code", ""), b.get("src", "record")),
    "/api/verify/apply": lambda b: {"code": verify.apply(b.get("code", ""), b.get("ids") or [])},
    "/api/replay": lambda b: {"job": executor.start_replay(b.get("code", ""), b.get("name", ""), b.get("module", ""),
                                                           b.get("author", ""))},
    "/api/replay/retry": lambda b: {"job": executor.retry(b.get("job", ""))},
    "/api/save": lambda b: tests.save(b.get("code", ""), b.get("name", ""), b.get("module", ""), b.get("priority", ""),
                                      b.get("description", ""), b.get("author", ""), b.get("source", "written"),
                                      b.get("lines")),
    "/api/tests/save-draft": lambda b: tests.save_draft(b.get("id"), b.get("name", ""), b.get("module", ""),
                                                        b.get("author", ""), b.get("lines") or []),
    "/api/run": lambda b: {"run_id": executor.start_run(b.get("ids") or [], {
        "video": b.get("video", True), "shots": b.get("shots", True), "bugpack": b.get("bugpack", True),
        "stop_first": b.get("stop_first", False)}, b.get("who", ""))},
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, body, ctype="application/json", extra: dict | None = None):
        data = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str))

    def _call(self, fn, arg):
        try:
            self._json(fn(arg))
        except Bad as e:
            self._json({"error": str(e)}, 400)
        except (ValueError, state.AIBlocked) as e:
            self._json({"error": str(e)}, 400)
        except KeyError as e:
            self._json({"error": str(e.args[0]) if e.args else "not found"}, 404)
        except Exception:  # noqa: BLE001
            tb = traceback.format_exc()
            sys.stderr.write(tb)
            self._json({"error": "Something went wrong inside Test Studio: " + tb.strip().splitlines()[-1][:200]}, 500)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
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
            except (KeyError, FileNotFoundError):
                return self._json({"error": "That file does not exist for this run."}, 404)
            except Exception as e:  # noqa: BLE001
                return self._json({"error": str(e)[:200]}, 500)
        if u.path == "/api/runs/file":
            try:
                p = tests.run_file(_q(q, "id"), _q(q, "name"))
                return self._send(200, p.read_bytes(), "image/png")
            except Exception:  # noqa: BLE001
                return self._send(404, "not found", "text/plain")
        fn = GET.get(u.path)
        if not fn:
            return self._json({"error": "not found"}, 404)
        self._call(fn, q)

    def do_POST(self):
        fn = POST.get(urlparse(self.path).path)
        if not fn:
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        except ValueError:
            return self._json({"error": "Request was not valid JSON."}, 400)
        self._call(fn, body)


def main():
    from ui import envs
    envs.apply_active()
    try:
        settings.validate()
    except RuntimeError as e:      # a new PC has no .env yet; the Settings screen is where it is filled in
        print("\n  Note: login details are not set yet (" + str(e).splitlines()[0] + ").")
        print("  Open Settings in the UI and fill them in.")
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\n{'=' * 52}\n  MargBooks Test Studio is running\n  {url}\n  Press Ctrl+C to stop\n{'=' * 52}\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
