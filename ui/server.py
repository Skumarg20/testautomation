"""
Local web UI -- sirf Python ki apni library se, koi extra install nahi.

    python -m ui.server        (ya ui.bat)
    -> http://localhost:8777

Yahan sirf HTTP aur JSON hai. Asli kaam framework/ aur pages/ karte hain --
wahi code jo pytest se chalta hai. Do alag raste rakhne se dono kabhi ek
jaise nahi rehte.
"""
from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from config.settings import settings, ROOT
from ui import store, runner, importer, nl, envs, codegen_import, tools
from framework import ai as ai_mod

HERE = Path(__file__).resolve().parent
PORT = 8777


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):        # console saaf rakho
        pass

    # ---------- helpers ----------

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str))

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except Exception:  # noqa: BLE001
            return {"_raw": raw}

    # ---------- GET ----------

    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)

        if p in ("/", "/index.html"):
            return self._send(200, (HERE / "app.html").read_bytes(), "text/html; charset=utf-8")

        if p == "/api/tests":
            return self._json({"tests": store.as_dicts()})

        if p == "/api/meta":
            return self._json({
                "examples": nl.examples(),
                **importer.valid_targets(),
                "allow_destructive": settings.ALLOW_DESTRUCTIVE,
                "company": settings.COMPANY,
                "app_url": settings.BASE_URL,
                "env": envs.listing()["active"],
                "build": settings.BUILD,
                "ai": ai_mod.available(),
                "catalogue": __import__("framework.catalogue",
                                        fromlist=["catalogue"]).stats(),
            })

        if p == "/api/run":
            rid = (q.get("id") or [""])[0]
            r = runner.get(rid)
            return self._json(r or {"error": "run not found"}, 200 if r else 404)

        if p == "/api/catalogue":
            from framework import catalogue
            sc = (q.get("screen") or [""])[0]
            if sc:
                return self._json({"screen": sc,
                                   "elements": catalogue.screen_elements(sc)})
            return self._json(catalogue.stats())

        if p == "/api/menu":
            from framework import menu_tree
            from pages.registry import describe
            tests = store.as_dicts()
            counts: dict[str, int] = {}
            for t in tests:
                counts[t.get("menu_id") or ""] = counts.get(
                    t.get("menu_id") or "", 0) + 1
            return self._json({"tree": menu_tree.tree_for_ui(),
                               "counts": counts,
                               "pom": describe()})

        if p == "/api/tools":
            return self._json({**tools.listing(), **tools.recent()})

        if p == "/api/tools/log":
            return self._json(tools.status(
                (q.get("job") or [""])[0],
                int((q.get("since") or ["0"])[0] or 0)))

        if p == "/api/scan":
            from framework import code_scanner
            return self._json(code_scanner.stats())

        if p == "/api/logs":
            from framework import logbook
            kind = (q.get("kind") or ["execution"])[0]
            return self._json({"kind": kind, "lines": logbook.tail(kind, 120),
                               "history": logbook.summary()})

        if p == "/api/spec":
            # Test ka code -- Playwright script ki tarah dekhne ke liye
            return self._json(store.as_spec((q.get("id") or [""])[0]))

        if p == "/api/control-room":
            from framework import control_room
            saved = control_room.load()
            # The saved file keeps the description from the day it was read.
            # Always show the current wording from prerequisites.json.
            for key, row in (saved.get("settings") or {}).items():
                if key in control_room.KNOWN:
                    row["affects"] = control_room.KNOWN[key]["affects"]
            return self._json({**saved,
                               "summary": control_room.summary(),
                               "known": {k: v["affects"]
                                         for k, v in control_room.KNOWN.items()}})

        if p == "/api/ai":
            return self._json(ai_mod.available())

        if p == "/api/envs":
            return self._json(envs.listing())

        if p == "/api/runs":
            return self._json({"runs": runner.recent()})

        if p == "/api/test":
            d = store.detail((q.get("id") or [""])[0])
            return self._json(d or {"error": "test not found"}, 200 if d else 404)

        if p == "/api/template.csv":
            return self._send(200, importer.template_csv().encode(),
                              "text/csv; charset=utf-8")

        return self._send(404, "not found", "text/plain")

    # ---------- POST ----------

    def do_POST(self):
        p = urlparse(self.path).path
        b = self._body()

        if p == "/api/run":
            ids = b.get("ids") or []
            if not ids:
                return self._json({"error": "no tests selected"}, 400)
            rid = runner.submit(ids, b.get("who", ""))
            return self._json({"run_id": rid})

        if p == "/api/ai/save":
            try:
                ai_mod.save_key(b.get("provider", "gemini"),
                                b.get("key", ""), b.get("model", ""))
                return self._json({**ai_mod.available(), **ai_mod.check()})
            except Exception as e:  # noqa: BLE001
                return self._json({"error": str(e)}, 400)

        if p == "/api/ai/models":
            # Google se live list. Model ke naam badalte rehte hain --
            # code me likhe naam purane pad jate hain (404 aata hai).
            try:
                key = b.get("key") or ai_mod.gemini_key()
                models = ai_mod.list_models(key)
                return self._json({"models": models,
                                   "best": ai_mod.pick_model(models)})
            except Exception as e:  # noqa: BLE001
                return self._json({"error": str(e), "models": []}, 200)

        if p == "/api/ai/test":
            return self._json(ai_mod.check())

        if p == "/api/env/save":
            try:
                return self._json(envs.upsert(b))
            except Exception as e:  # noqa: BLE001
                return self._json({"error": str(e)}, 400)

        if p == "/api/env/writes":
            # Sirf ye ek setting badalta hai. Poora modal kholna sirf
            # writes on/off karne ke liye zyada hai.
            d = envs.load()
            e = d["envs"].get(b.get("name", ""))
            if not e:
                return self._json({"error": "environment not found"}, 400)
            e["allow_writes"] = bool(b.get("on"))
            envs.save(d)
            envs.apply_active()
            return self._json({"name": e["name"], "allow_writes": e["allow_writes"]})

        if p == "/api/env/use":
            ok = envs.activate(b.get("name", ""))
            if ok:
                envs.apply_active()
            return self._json({"active": b.get("name")} if ok
                              else {"error": "environment not found"},
                              200 if ok else 400)

        if p == "/api/env/delete":
            ok = envs.remove(b.get("name", ""))
            return self._json({"deleted": ok}, 200 if ok else 400)

        if p == "/api/scan":
            from framework import code_scanner
            path = (b.get("path") or "").strip()
            if not path:
                return self._json({"error": "Folder ka path do"}, 400)
            try:
                data = code_scanner.scan(path, verbose=False)
                return self._json({**code_scanner.stats(),
                                   "routes": data["routes"][:40]})
            except FileNotFoundError as e:
                return self._json({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001
                return self._json({"error": f"Scan nahi ho paya: {e}"}, 400)

        if p == "/api/codegen":
            try:
                res = codegen_import.to_case(
                    b.get("script", ""), name=b.get("name") or "Recorded test",
                    description=b.get("description", ""),
                    module=b.get("module", ""))
                return self._json(res)
            except Exception as e:  # noqa: BLE001
                return self._json({"error": str(e)}, 400)

        if p == "/api/tools/run":
            return self._json(tools.start(b.get("id", ""),
                                          b.get("flags") or [],
                                          [a for a in (b.get("args") or []) if a]))

        if p == "/api/tools/stop":
            return self._json(tools.stop(b.get("job", "")))

        if p == "/api/map":
            # Steps ka har target -> asli element, bharose ke saath.
            # Ye SAVE SE PEHLE dikhaya jata hai.
            from framework import mapping
            return self._json(mapping.map_steps(b.get("steps") or [],
                                                screen=b.get("screen", "")))

        if p == "/api/parse":
            # Saadhi bhasha -> steps. Kuch save nahi hota, sirf dikhaya jata hai.
            use_ai = bool(b.get("ai", True))
            fn = nl.parse_with_ai if use_ai else nl.parse
            try:
                return self._json(fn(b.get("text", "")))
            except Exception as e:  # noqa: BLE001
                return self._json(nl.parse(b.get("text", "")) | {
                    "ai_used": False, "ai_note": str(e)[:200]})

        if p == "/api/save":
            try:
                res = store.save(
                    name=b.get("name", ""), description=b.get("description", ""),
                    module=b.get("module", "general"), steps=b.get("steps") or [],
                    author=b.get("author", ""), tags=b.get("tags") or [],
                    destructive=bool(b.get("destructive")),
                    case_id=b.get("id") or None)
                return self._json(res)
            except Exception as e:  # noqa: BLE001
                return self._json({"error": str(e)}, 400)

        if p == "/api/delete":
            cid = b.get("id", "")
            d = store.detail(cid)
            if not d:
                return self._json({"error": "test not found"}, 404)
            if not d["editable"]:
                return self._json({
                    "error": f"'{cid}' built-in test hai ({d['source']}). "
                             f"Ise mitaya nahi ja sakta -- agle update me wapas "
                             f"aa jayega. Chalana band karna ho to use chuno mat."
                }, 400)
            return self._json({"deleted": store.delete(cid)})

        if p == "/api/import":
            raw = b.get("_raw")
            text = b.get("csv")
            try:
                if text:
                    tests, warns = importer.parse_csv(text)
                elif raw:
                    tests, warns = importer.parse_xlsx(raw)
                else:
                    return self._json({"error": "no file received"}, 400)
            except Exception as e:  # noqa: BLE001
                return self._json({"error": f"could not read the file: {e}"}, 400)
            return self._json({"tests": tests, "warnings": warns})

        if p == "/api/import/save":
            saved, errs = [], []
            for t in b.get("tests") or []:
                try:
                    saved.append(store.save(
                        name=t.get("name", ""), description=t.get("description", ""),
                        module=t.get("module", "general"), steps=t.get("steps") or [],
                        author=b.get("author", "")))
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{t.get('name')}: {e}")
            return self._json({"saved": saved, "errors": errs})

        return self._send(404, "not found", "text/plain")


def main():
    envs.apply_active()          # UI me chuna hua environment
    settings.validate()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\n{'='*52}")
    print(f"  MargBooks QA — UI is running")
    print(f"  {url}")
    print(f"  build {settings.BUILD}")
    print(f"  Company: {settings.COMPANY}")
    print(f"  Tests that write data: "
          f"{'WILL RUN' if settings.ALLOW_DESTRUCTIVE else 'will be skipped'}")
    print(f"\n  Press Ctrl+C to stop")
    print(f"{'='*52}\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
