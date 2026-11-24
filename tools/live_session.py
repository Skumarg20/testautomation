"""
One logged-in MargBooks browser, kept open, driven over local HTTP. Used to verify test cases by hand
(as a user would) and to run their steps, without signing in again for every case.

    python -m tools.live_session --port 8801 --company "QA Chemist" [--writes]

Endpoints (JSON in, JSON out; all on 127.0.0.1 only):
  GET  /state                 url, company, page heading, visible buttons/tabs (short)
  POST /run   {"steps":[...]} run Studio steps; per-step OK/FAIL, error, screenshot of a failure
  POST /py    {"code": "..."} run Python with page, bp, settings, cr (control_room), qa (qa_company);
                              print() output and a variable `result` come back
  POST /shot  {"name": "x"}   screenshot of the viewport, returns its path (open it to look)
  POST /reset                 close popups/forms, back to the dashboard of the session's company
  POST /company {"name": ""}  switch company (writes stay limited to QA test companies)
  GET  /toasts                messages the app showed since the last call

Writes (--writes): allowed only while a QA test company is open; every step that can change data checks
the header first (framework.qa_company). Without --writes the project's click guard blocks Save/Delete.
One request at a time per session (the browser is single-threaded).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "artifacts" / "verify" / "shots"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--writes", action="store_true")
    a = ap.parse_args()

    os.environ["MB_NO_CAPTURE"] = "1"
    os.environ.setdefault("HEADLESS", "true")
    from config.settings import settings
    settings.ALLOW_DESTRUCTIVE = bool(a.writes)
    type(settings).ALLOW_DESTRUCTIVE = bool(a.writes)

    from playwright.sync_api import sync_playwright
    from framework import control_room as cr, qa_company as qa, safety
    from framework.auth import app_ready, login
    from framework.browser import launch
    from framework.step_runner import RunContext, StepRunner

    if a.writes and not qa.is_test_company(a.company):
        raise SystemExit(f"--writes is only allowed for QA test companies, not {a.company!r}")
    SHOTS.mkdir(parents=True, exist_ok=True)

    lock = threading.Lock()
    jobs: list = []                    # (fn, holder, event) -> run on the Playwright thread
    S: dict = {}

    def session_up():
        # MargBooks allows one tab per browser ("MargBooks is open in another tab/window"): close every
        # tab of this browser before signing in again; if that is not enough, start a fresh browser.
        for pg in list(S["ctx"].pages):
            try:
                pg.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            bp = login(S["ctx"].new_page(), verbose=False)
        except Exception:  # noqa: BLE001
            try:
                S["browser"].close()
            except Exception:  # noqa: BLE001
                pass
            S["browser"], S["ctx"] = launch(S["pw"])
            bp = login(S["ctx"].new_page(), verbose=False)
        qa.switch(bp.page, a.company)
        if a.writes:
            cr.allow_settings_change(True)
        S["bp"] = bp
        S["toasts_seen"] = 0

    def ensure():
        bp = S.get("bp")
        if bp is None or not (app_ready(bp.page, 3000) or app_ready(bp.page, 15000)):   # 2nd look: slow screen
            session_up()
        if a.writes and not qa.is_test_company(qa.current(S["bp"].page)):
            qa.switch(S["bp"].page, a.company)
        return S["bp"]

    def shot(name: str) -> str:
        path = SHOTS / f"{int(time.time())}_{a.port}_{''.join(c if c.isalnum() else '_' for c in name)[:60]}.png"
        try:
            S["bp"].page.screenshot(path=str(path), timeout=8000)
            return str(path)
        except Exception as e:  # noqa: BLE001
            return f"(no screenshot: {e})"

    def state() -> dict:
        bp = ensure()
        pg = bp.page
        info = pg.evaluate("""() => {
          const vis = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const txt = sel => [...document.querySelectorAll(sel)].filter(vis)
              .map(e => (e.innerText || e.value || e.title || '').trim().replace(/\\s+/g, ' ')).filter(t => t && t.length < 60);
          return {heading: txt('h1,h2,h3,h4,h5,.page-title,.title,.card-title').slice(0, 8),
                  buttons: [...new Set(txt('button,[role=button],a.btn'))].slice(0, 60),
                  tabs: [...new Set(txt('[role=tab],.nav-tabs a,.nav-link,.mat-tab-label'))].slice(0, 30),
                  modal: txt('.modal.show .modal-body,.swal2-html-container,[role=dialog]').slice(0, 3)};
        }""")
        return {"url": pg.url.split("?")[0], "company": qa.current(pg), **info}

    def run_steps(steps: list) -> dict:
        bp = ensure()
        bp.page.set_default_timeout(60000)          # /py may have lowered it; the runner expects the normal one
        bp.page.set_default_navigation_timeout(120000)
        out, ok = [], True
        runner = StepRunner(bp, RunContext())
        runner.auto_undo = False                    # steps run one by one here: a set_setting must stay set
        for i, st in enumerate(steps, 1):
            t0 = time.time()
            try:
                runner.run([st])
                out.append({"i": i, "ok": True, "secs": round(time.time() - t0, 1), "step": st.get("note") or st.get("action")})
            except BaseException as e:  # noqa: BLE001  (StepFailed, pytest Skipped, Playwright errors)
                ok = False
                out.append({"i": i, "ok": False, "secs": round(time.time() - t0, 1),
                            "step": st.get("note") or st.get("action"),
                            "kind": type(e).__name__, "error": str(e)[:1500], "shot": shot(f"fail_step{i}")})
                # clean-up steps (always: true) still run after a failure
                for j, cst in enumerate(steps[i:], i + 1):
                    if cst.get("always"):
                        try:
                            runner.run([{**cst, "always": False}])
                            out.append({"i": j, "ok": True, "cleanup": True, "step": cst.get("note") or cst.get("action")})
                        except BaseException as ce:  # noqa: BLE001
                            out.append({"i": j, "ok": False, "cleanup": True,
                                        "step": cst.get("note") or cst.get("action"), "error": str(ce)[:300]})
                            break                      # a failed clean-up check must block what follows it
                break
        return {"ok": ok, "results": out, "url": bp.page.url.split("?")[0], "log": runner.ctx.log[-30:]}

    def run_py(code: str) -> dict:
        bp = ensure()
        bp.page.set_default_timeout(10000)          # explore fast: a wrong selector fails in 10 s, not 60 s
        g = {"page": bp.page, "bp": bp, "settings": settings, "cr": cr, "qa": qa, "safety": safety,
             "time": time, "result": None}
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(code, "<py>", "exec"), g)  # noqa: S102  (local tool, 127.0.0.1 only)
            return {"ok": True, "stdout": buf.getvalue()[-20000:], "result": _jsonable(g.get("result"))}
        except BaseException as e:  # noqa: BLE001
            return {"ok": False, "stdout": buf.getvalue()[-8000:], "error": f"{type(e).__name__}: {e}"[:3000],
                    "trace": traceback.format_exc()[-2500:]}

    def reset() -> dict:
        bp = ensure()
        try:
            safety.force_close_modal(bp.page)
        except Exception:  # noqa: BLE001
            pass
        try:
            from framework.screens_check import ensure_neutral
            ensure_neutral(bp)
        except Exception:  # noqa: BLE001
            pass
        bp.page.goto(settings.BASE_URL + "/dashboard", wait_until="domcontentloaded")
        bp.page.wait_for_timeout(3000)
        return state()

    def toasts() -> dict:
        bp = ensure()
        all_ = safety.get_toasts(bp.page)
        new = all_[S.get("toasts_seen", 0):]
        S["toasts_seen"] = len(all_)
        return {"toasts": new}

    def company(name: str) -> dict:
        bp = ensure()
        if a.writes and not qa.is_test_company(qa.BY_TRADE.get(name.lower(), name)):
            return {"ok": False, "error": "this session has writes on; only QA test companies are allowed"}
        qa.switch(bp.page, name)
        a.company = qa.current(bp.page)
        return {"ok": True, **state()}

    routes = {
        ("GET", "/state"): lambda b: state(),
        ("GET", "/toasts"): lambda b: toasts(),
        ("POST", "/run"): lambda b: run_steps(b.get("steps") or []),
        ("POST", "/py"): lambda b: run_py(b.get("code") or ""),
        ("POST", "/shot"): lambda b: {"path": (ensure() and shot(b.get("name") or "shot"))},
        ("POST", "/reset"): lambda b: reset(),
        ("POST", "/company"): lambda b: company(b.get("name") or ""),
    }

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):  # quiet
            pass

        def _do(self, method):
            fn = routes.get((method, self.path.split("?")[0]))
            if not fn:
                self._send(404, {"error": "unknown endpoint"})
                return
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            except Exception:  # noqa: BLE001
                self._send(400, {"error": "body is not JSON"})
                return
            holder, ev = {}, threading.Event()
            with lock:
                jobs.append((lambda: fn(body), holder, ev))
            ev.wait(1800)
            self._send(200, holder.get("out", {"error": holder.get("err", "timed out after 1800 s")}))

        def do_GET(self):
            self._do("GET")

        def do_POST(self):
            self._do("POST")

        def _send(self, code, obj):
            data = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    with sync_playwright() as pw:
        S["pw"] = pw
        S["browser"], S["ctx"] = launch(pw)
        session_up()
        print(f"READY port={a.port} company={qa.current(S['bp'].page)} writes={a.writes}", flush=True)
        while True:
            job = None
            with lock:
                if jobs:
                    job = jobs.pop(0)
            if job is None:
                try:
                    S["bp"].page.wait_for_timeout(200)     # keeps Playwright's event loop serviced
                except Exception:  # noqa: BLE001
                    time.sleep(0.2)
                continue
            fn, holder, ev = job
            try:
                holder["out"] = fn()
            except BaseException as e:  # noqa: BLE001
                holder["err"] = f"{type(e).__name__}: {str(e)[:1500]}"
            ev.set()


def _jsonable(v):
    try:
        json.dumps(v, default=str)
        return v
    except Exception:  # noqa: BLE001
        return repr(v)[:5000]


if __name__ == "__main__":
    main()
