"""
Saved tests, runs and downloads for Test Studio.

A saved test is BOTH: testcases/saved/TC_006.yaml (what the runner executes) and
<out_dir>/<module>/tc-006-<slug>.spec.ts (what developers read). Details the YAML has no
place for (author, priority, written lines) live in config/studio.db.
"""
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from pathlib import Path

from ui_studio import grammar, script, state

MODULE_YAML = {"Sale": "sales", "Purchase": "purchase", "Inventory": "inventory", "Accounts": "accounting",
               "Masters": "masters", "Control Room": "control_room", "Reports": "reports", "CRM": "crm"}
YAML_MODULE = {v: k for k, v in MODULE_YAML.items()}


def module_label(m: str) -> str:
    m = (m or "general").strip()
    return YAML_MODULE.get(m.lower()) or YAML_MODULE.get(m) or (m if m in MODULE_YAML else m.replace("_", " ").title())


def display_id(yaml_id: str) -> str:
    return yaml_id.replace("_", "-") if re.fullmatch(r"TC_\d{3,}", yaml_id) else yaml_id


def yaml_id(disp: str) -> str:
    return disp.replace("-", "_") if re.fullmatch(r"TC-\d{3,}", disp) else disp


def _author(case) -> tuple[str, str]:
    for pre in (case.preconditions or []):
        if pre.startswith("Created by "):
            a, _, d = pre[len("Created by "):].partition("|")
            return a.strip(), d.strip()
    return "", ""


def _meta(tid: str) -> dict | None:
    with state.db() as c:
        r = c.execute("SELECT * FROM tests WHERE id=?", (tid,)).fetchone()
    return dict(r) if r else None


def list_tests() -> list[dict]:
    from ui import store
    out = []
    M = grammar.Memory()
    for c in store.list_all():
        d = display_id(c.id)
        meta = _meta(d)
        a, dt = _author(c)
        lines = json.loads(meta["lines"]) if meta and meta["lines"] else None
        bad = 0
        if lines:
            res, _ = grammar.parse_all(lines, M)
            bad = sum(1 for r in res if r["status"] == "bad")
        kind = (meta["kind"] if meta else ("written" if c.source_file.startswith("saved") else "builtin"))
        out.append({"id": d, "name": c.title, "module": module_label(c.module),
                    "author": (meta["author"] if meta else a) or a or "unknown", "date": (meta["created"] if meta else dt) or dt,
                    "type": "recorded" if kind == "record" else kind, "steps": len(c.steps), "bad": bad,
                    "lines": lines, "editable": c.source_file.startswith("saved"),
                    "draft": bool(getattr(c, "draft", False))})
    # drafts that still have red lines exist only in the database
    have = {t["id"] for t in out}
    with state.db() as con:
        for r in con.execute("SELECT * FROM tests WHERE kind='draft'").fetchall():
            if r["id"] in have:
                continue
            lines = json.loads(r["lines"] or "[]")
            res, _ = grammar.parse_all(lines, M)
            out.append({"id": r["id"], "name": r["name"], "module": r["module"], "author": r["author"],
                        "date": r["created"], "type": "written", "steps": len([x for x in res if x["status"] == "ok"]),
                        "bad": sum(1 for x in res if x["status"] == "bad"), "lines": lines, "editable": True,
                        "draft": True})
    return sorted(out, key=lambda t: (t["module"], t["id"]))


def open_test(tid: str) -> dict:
    meta = _meta(tid)
    if not meta:
        raise KeyError("test not found")
    return {"id": tid, "name": meta["name"], "module": meta["module"], "author": meta["author"],
            "lines": json.loads(meta["lines"] or "[]"), "code": meta["code"] or ""}


def load_cases(ids: list[str]) -> list[dict]:
    from ui import store
    cases = []
    for disp in ids:
        c = store.get(yaml_id(disp))
        if not c:
            raise KeyError(f"{disp}: test not found or has no runnable steps")
        meta = _meta(disp)
        a, _ = _author(c)
        cases.append({"id": c.id, "display_id": disp, "name": c.title, "module": module_label(c.module),
                      "author": (meta["author"] if meta else a) or a or "unknown",
                      "steps": [dict(s) for s in c.steps], "destructive": bool(c.destructive)})
    return cases


def _clean(steps: list[dict]) -> list[dict]:
    return [{k: v for k, v in s.items() if not k.startswith("_")} for s in steps]


def _slug_file(tid: str, name: str) -> str:
    return f"{tid.lower()}-{script.slug(name)}.spec.ts"


def _write_spec(tid: str, name: str, module: str, author: str, description: str, code: str) -> str:
    out = Path(state.load_settings()["out_dir"]) / script.slug(module) / _slug_file(tid, name)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = code.split("\n")
    head = [f"// {tid} · {name} · module: {module}", f"// Written by: {author}"]
    if description.strip():
        head.append(f"// Description: {description.strip()[:300]}")
    lines = [ln for ln in lines if not ln.startswith(("// TC-", "// Written by:", "// Description:"))]
    out.write_text("\n".join(head + lines), encoding="utf-8")
    return str(out)


def save(code: str, name: str, module: str, priority: str, description: str, author: str, source: str,
         lines: list[str] | None = None) -> dict:
    from ui import store
    name, author = (name or "").strip(), (author or "").strip()
    if not module or not name or not author:
        raise ValueError("Module, test case name and Written by are required.")
    conv = script.to_steps(code)
    if conv["unknown"] or not conv["steps"]:
        raise ValueError("The script has lines that cannot be replayed; fix them and replay again before saving.")
    seq = state.next_seq()
    tid = state.tc_id(seq)
    steps = _clean(conv["steps"])
    writes = any(s.get("action") in ("save_form", "set_party", "add_item", "bulk_sale_bills", "retail_bill") for s in steps)
    res = store.save(name=name, description=description, module=MODULE_YAML.get(module, module.lower().replace(" ", "_")),
                     steps=steps, author=author, tags=["studio", f"priority-{(priority or 'Medium').lower()}"],
                     destructive=writes, case_id=yaml_id(tid))
    spec = _write_spec(tid, name, module, author, description, code)
    with state.db() as c:
        c.execute("INSERT OR REPLACE INTO tests VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tid, name, module, author, priority or "Medium", description,
                   "record" if source == "record" else "written", time.strftime("%d-%b-%Y"),
                   json.dumps(lines) if lines else None, code, spec, seq))
    return {"id": tid, "yaml": res["file"], "spec": spec}


def save_draft(tid: str | None, name: str, module: str, author: str, lines: list[str]) -> dict:
    """Write screen's 'Save draft'. Runnable (YAML written) only when every line is mapped."""
    from ui import store
    lines = [ln for ln in lines if ln.strip()]
    if not name.strip():
        raise ValueError("Give the test case a name.")
    if not lines:
        raise ValueError("Write at least one step.")
    res, _ = grammar.parse_all(lines)
    clean = all(r["status"] != "bad" for r in res)
    if tid and not _meta(tid):
        tid = None
    seq = None
    if not tid:
        seq = state.next_seq()
        tid = state.tc_id(seq)
    else:
        seq = _meta(tid)["seq"]
    code = None
    if clean:
        steps = grammar.to_steps(lines)
        writes = any(s.get("action") in ("save_form", "set_party", "add_item", "bulk_sale_bills") for s in steps)
        store.save(name=name, description="", module=MODULE_YAML.get(module, module.lower()), steps=steps,
                   author=author, tags=["studio", "draft-lines"], destructive=writes, case_id=yaml_id(tid))
        code = script.generate(name, module, author, lines, tid)["code"]
    with state.db() as c:
        c.execute("INSERT OR REPLACE INTO tests VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tid, name, module, author, "Medium", "", "written" if clean else "draft",
                   time.strftime("%d-%b-%Y"), json.dumps(lines), code, "", seq))
    return {"id": tid, "runnable": clean}


# ------------------------------------------------------------------ runs

def list_runs() -> dict:
    with state.db() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY ts DESC LIMIT 300").fetchall()
    runs = [{"id": r["id"], "test": r["test_id"], "name": r["name"], "module": r["module"], "author": r["author"],
             "at": r["at"], "passed": r["passed"], "total": r["total"], "result": r["result"], "err": r["err"],
             "failAt": r["fail_at"]} for r in rows]
    p = sum(1 for r in runs if r["result"] == "Pass")
    return {"runs": runs, "kpis": {"runs": len(runs), "passed": p, "failed": len(runs) - p,
                                    "testers": len({r["author"] for r in runs})}}


def _run_row(rid: str) -> dict:
    with state.db() as c:
        r = c.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
    if not r:
        raise KeyError("run not found")
    return dict(r)


def run_detail(rid: str) -> dict:
    r = _run_row(rid)
    d = Path(r["dir"])
    shots = sorted(p.name for p in d.glob("*.png")) if d.exists() else []
    steps = json.loads(r["steps"] or "[]")
    return {"run": {"id": r["id"], "test": r["test_id"], "name": r["name"], "module": r["module"], "author": r["author"],
                    "at": r["at"], "passed": r["passed"], "total": r["total"], "result": r["result"], "err": r["err"],
                    "failAt": r["fail_at"], "aiFixes": r["ai_fixes"]},
            "steps": [{"text": s["text"], "status": {"ok": "Pass", "bad": "Fail", "skip": "Skip"}.get(s["status"], "Skip")}
                      for s in steps],
            "files": {"video": (d / "run.webm").exists(), "trace": (d / "trace.zip").exists(),
                      "screens": [{"name": n, "url": f"/api/runs/file?id={rid}&name={n}"} for n in shots]}}


def run_file(rid: str, name: str) -> Path:
    d = Path(_run_row(rid)["dir"]).resolve()
    p = (d / Path(name).name).resolve()
    if p.parent != d or not p.exists():
        raise KeyError("file not found")
    return p


def _steps_for_test(disp: str) -> list[dict]:
    from ui import store
    c = store.get(yaml_id(disp))
    if not c:
        raise KeyError("test not found")
    return _clean(c.steps)


def spec_text(disp: str) -> str:
    meta = _meta(disp)
    if meta and meta["code"]:
        return meta["code"]
    from ui import store
    return store.as_spec(yaml_id(disp)).get("code", "")


def recorder_for_test(disp: str) -> str:
    from ui import envs
    env = envs.apply_active() or {}
    routes = {m["key"]: m["route"] for m in grammar.Memory().screens.values() if m["route"]}
    return script.recorder_json(disp, env.get("app_url", ""), _steps_for_test(disp), routes)


def report_html(rid: str) -> str:
    from html import escape as e
    d = run_detail(rid)
    r, st = d["run"], d["steps"]
    rows = "".join(f"<tr><td>{i + 1}</td><td>{e(s['text'])}</td><td class='{s['status']}'>{s['status']}</td></tr>"
                   for i, s in enumerate(st))
    err = f"<p class='Fail'>{e(r['err'])}</p>" if r["err"] else ""
    return (f"<!doctype html><meta charset='utf-8'><title>{e(r['id'])}</title><style>body{{font-family:Segoe UI,Arial;margin:24px}}"
            f"td,th{{border:1px solid #ccc;padding:6px 10px;text-align:left}}table{{border-collapse:collapse}}"
            f".Pass{{color:#14874A}}.Fail{{color:#D23A3A}}</style><h1>{e(r['id'])} · {e(r['test'])} {e(r['name'])}</h1>"
            f"<p>Module: {e(r['module'])} · Written by: <b>{e(r['author'])}</b> · Run: {e(r['at'])} · "
            f"Result: <b class='{r['result']}'>{r['result']}</b> ({r['passed']}/{r['total']})</p>{err}"
            f"<table><tr><th>#</th><th>Step</th><th>Result</th></tr>{rows}</table>")


def bug_pack(rid: str) -> bytes:
    """One zip for developers. Never contains a password."""
    from ui import envs
    r = _run_row(rid)
    d = Path(r["dir"])
    env = envs.apply_active() or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("run.webm", "trace.zip"):
            if (d / name).exists():
                z.write(d / name, name)
        for p in sorted(d.glob("*.png")) if d.exists() else []:
            z.write(p, f"screenshots/{p.name}")
        z.writestr("test.spec.ts", spec_text(r["test_id"]))
        z.writestr("recorder.json", recorder_for_test(r["test_id"]))
        steps = json.loads(r["steps"] or "[]")
        z.writestr("steps.txt", f"{r['test_id']} {r['name']}\nWritten by: {r['author']}\nResult: {r['result']}\n"
                   + (f"Error: {r['err']}\n" if r["err"] else "") + "\n"
                   + "\n".join(f"{i + 1}. [{s['status']}] {s['text']}" for i, s in enumerate(steps)))
        z.writestr("env.txt", f"URL: {env.get('app_url', '')}\nCompany: {env.get('company', '')}\n"
                   f"Trade: {__import__('ui_studio.memory', fromlist=['memory']).build().get('trade', '')}\nBrowser: Chromium (Playwright)\n")
        z.writestr("ai_fixes.txt", "AI fixes are recorded in the saved script header and the Studio AI usage log.\n")
    return buf.getvalue()
