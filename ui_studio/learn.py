"""
Learn the app: the project's own crawler does the walking; this module starts it, follows its output
and turns that into the six numbered steps on the Learn screen. Also: restore settings, read source code.
"""
from __future__ import annotations

import re

from ui import tools
from ui_studio import state

WALK = [("login", "Log in", r"sign(ed)? in|logged in|login ok|login"),
        ("trade", "Detect business type", r"trade|business type|company type"),
        ("backup", "Back up settings", r"back(ed)? ?up|saved .*settings|control_room_backup"),
        ("cr", "Turn on all trade settings", r"turn(ed)? on|enabl(e|ed|ing) (all )?setting|settings? (on|enabled)"),
        ("menu", "Enable all menus", r"menu"),
        ("crawl", "Open each menu, record fields", r"crawl|opening|screen|page|field|element")]


def start() -> dict:
    s = state.load_settings()
    if not s["test_company"]:
        raise ValueError("Learn the app changes Control Room settings. Tick “This is a test company” "
                         "in Settings first, and only do it on a test company.")
    r = tools.start("crawler", ["--enable"], ["--minutes", "90"])
    if "error" in r:
        raise ValueError(r["error"])
    return {"job": r["job"]}


def restore() -> dict:
    r = tools.start("restore")
    if "error" in r:
        raise ValueError(r["error"])
    return {"job": r["job"]}


def status(job: str, since: int = 0) -> dict:
    st = tools.status(job, 0)
    if "error" in st:
        raise KeyError(st["error"])
    lines = st["lines"]
    reached = -1
    for i, (_, _, pat) in enumerate(WALK):
        if any(re.search(pat, ln, re.I) for ln in lines):
            reached = max(reached, i)
    done = st["status"] != "running"
    steps = []
    for i, (k, _label, _p) in enumerate(WALK):
        if st["status"] == "done" or (done and st["status"] != "failed" and i <= reached):
            s_ = "done"
        elif i < reached:
            s_ = "done"
        elif i == reached and not done:
            s_ = "doing"
        else:
            s_ = "todo"
        steps.append({"k": k, "state": s_, "hint": ""})
    new = lines[since:]
    state_ = {"running": "running", "done": "done"}.get(st["status"], "failed")
    return {"state": state_, "steps": steps, "log": "\n".join(new) + ("\n" if new else ""), "next": len(lines),
            "seconds": st["seconds"]}


def read_code(web: str, api: str) -> dict:
    from framework import code_scanner
    web, api = (web or "").strip(), (api or "").strip()
    if not web and not api:
        raise ValueError("Give the Angular folder, the .NET folder, or both.")
    state.save_settings({"web_dir": web, "api_dir": api})
    elements = routes = 0
    msgs = []
    for p in (web, api):
        if not p:
            continue
        try:
            data = code_scanner.scan(p, verbose=False)
            msgs.append(f"{p}: {len(data.get('elements', []))} fields, {len(data.get('routes', []))} routes")
        except FileNotFoundError as e:
            raise ValueError(str(e))
    st = code_scanner.stats()
    return {"ok": True, "message": "; ".join(msgs), "elements": st.get("elements", 0), "routes": st.get("routes", 0)}
