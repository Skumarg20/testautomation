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
import threading
import time
import zipfile
from pathlib import Path

from ui_studio import grammar, script, state

MODULE_YAML = {"Sale": "sales", "Purchase": "purchase", "Inventory": "inventory", "Accounts": "accounting",
               "Masters": "masters", "Control Room": "control_room", "Reports": "reports", "CRM": "crm",
               "GST": "gst", "ABHA": "abha", "Online Store": "online_store"}
YAML_MODULE = {v: k for k, v in MODULE_YAML.items()}


def module_label(m: str) -> str:
    m = (m or "general").strip()
    return YAML_MODULE.get(m.lower()) or YAML_MODULE.get(m) or (m if m in MODULE_YAML else m.replace("_", " ").title())


def module_yaml(label: str) -> str:
    """'Sale' -> 'sales', 'Online Store' -> 'online_store'; '' or '*' -> '' (all modules)."""
    if not label or label == "*":
        return ""
    return MODULE_YAML.get(label, label.lower().replace(" ", "_"))


def display_id(yaml_id: str) -> str:
    return yaml_id.replace("_", "-") if re.fullmatch(r"TC_\d{3,}", yaml_id) else yaml_id


def yaml_id(disp: str) -> str:
    return disp.replace("-", "_") if re.fullmatch(r"TC-\d{3,}", disp) else disp


VERDICT_LABEL = {"verified": "Verified", "corrected": "Corrected", "app_defect": "App defect",
                 "blocked": "Blocked", "not_applicable": "Not applicable"}
SHOTS = Path(__file__).resolve().parents[1] / "artifacts" / "verify" / "shots"


def _company_trade(company: str) -> tuple[str, bool]:
    """'QA GST Chemist' -> ('chemist', True)."""
    from framework.qa_company import BY_TRADE, GST_BY_TRADE
    for t, c in BY_TRADE.items():
        if c == company:
            return t, False
    for t, c in GST_BY_TRADE.items():
        if c == company:
            return t, True
    return "", False


def _base_url() -> str:
    from config.settings import settings
    try:
        from ui import envs
        env = envs.apply_active() or {}
    except Exception:  # noqa: BLE001
        env = {}
    return (env.get("app_url") or settings.BASE_URL or "").rstrip("/")


def case_url(c) -> str:
    """The app URL a case works on: base URL + the route of the first screen its steps open."""
    from framework.screens import SCREENS
    base = _base_url()
    for st in c.steps or []:
        if st.get("action") == "goto" and st.get("target"):
            t = str(st["target"])
            return t if t.startswith("http") else base + "/" + t.lstrip("/")
        if st.get("action") == "open_screen" and st.get("target"):
            route = (SCREENS.get(str(st["target"])) or {}).get("url")
            if route:
                return base + route
    return base + "/dashboard" if base else ""


_SHORTCUT_SCREEN = {"alt+n": "Sale > Bill (new bill, Alt+N)", "alt+m": "Sale > Bill list (Alt+M)",
                    "alt+c": "Sale > Challan (Alt+C)", "alt+a": "Sale > Counter Sale (Alt+A)",
                    "alt+p": "Purchase > Bill (Alt+P)", "alt+i": "Master > Item list (Alt+I)",
                    "alt+l": "Master > Ledger (Alt+L)", "alt+k": "Sale > Stock Issue (Alt+K)"}


def case_where(c) -> str:
    """Which screen a manual tester opens: menu path of the first screen, a known shortcut, or a side-menu link."""
    from framework.screens import SCREENS
    found = []
    for st in c.steps or []:
        a, t, v = st.get("action"), str(st.get("target") or ""), str(st.get("value") or "")
        if a == "open_screen" and t:
            cfg = SCREENS.get(t) or {}
            path = " > ".join([str(cfg.get("menu") or "").title()] + [str(x) for x in cfg.get("path") or []]).strip(" >")
            found.append(path or t.replace("_", " ").title())
        elif a == "open_menu" and v:
            found.append(v)
        elif a == "press" and v.lower() in _SHORTCUT_SCREEN:
            found.append(_SHORTCUT_SCREEN[v.lower()])
        elif a in ("set_setting", "assert_setting"):
            found.append("Settings > Control Room")
    # helper screens (reading stock, setting a setting) come first in many scripts; show the screen the case is about
    helpers = ("Item list", "Control Room", "Ledger", "Dashboard")
    main = [f for f in found if not any(h in f for h in helpers)]
    out = list(dict.fromkeys(main or found))
    return " · then ".join(out[:3]) if out else (c.menu or "")


def ver_summary(c) -> dict | None:
    v = c.verification or {}
    if not v.get("status"):
        return None
    trade, gst = _company_trade(str(v.get("company") or ""))
    run = v.get("run") or {}
    return {"status": v["status"], "label": VERDICT_LABEL.get(v["status"], v["status"]),
            "company": v.get("company") or "", "trade": trade, "gst": gst, "date": str(v.get("date") or ""),
            "passed": run.get("passed"), "total": run.get("total"),
            "ready": v["status"] in ("verified", "corrected") and bool(c.steps)}


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


_LIST: dict = {"key": None, "out": None, "at": 0.0, "gen": 0, "built": 0}   # gen: Studio saves; built: gen checked
_LIST_LOCK = threading.Lock()
LIST_FRESH = 3.0          # seconds a checked list is served as it is (a whole team polls /api/tests)
_BODY: dict = {"of": None, "raw": b"", "gz": b""}   # the encoded /api/tests reply of the list object `of`
_BODY_LOCK = threading.Lock()


def invalidate_list():
    """A Studio save/delete changed a case: the next /api/tests checks again at once (not after LIST_FRESH), and
    nobody gets the old list while that check runs."""
    _LIST["at"] = 0.0
    _LIST["gen"] += 1


def _list_fresh() -> list[dict] | None:
    out = _LIST["out"]
    if out is not None and _LIST["key"] is not None and time.monotonic() - _LIST["at"] < LIST_FRESH:
        return list(out)
    return None


def list_tests() -> list[dict]:
    """Every case for the Test cases / Run screens. The list (1 MB+, grammar check of saved lines) is rebuilt
    only when a case file, a saved-test row, the e2e catalogue or app memory changed; one rebuild at a time.

    Checking whether anything changed (stat of every case file, the e2e catalogue, the tests table) itself costs
    0.5-2 s, so a list checked in the last LIST_FRESH seconds is returned without any of it and without the lock;
    requests that queued behind one check get that check's answer instead of each doing it again. Studio saves
    call invalidate_list(), so the QA who saved sees the change on the next load."""
    got = _list_fresh()
    if got is not None:
        return got
    return list(_list_checked())


def _list_checked() -> list[dict]:
    """The checked list itself (shared: callers must not change it). While one request checks for changes, the
    others get the last list at once instead of queueing behind the lock (parallel /api/tests took up to 13 s);
    only after a Studio save (dirty) or before the first build do they wait for the check."""
    if not _LIST_LOCK.acquire(blocking=False):
        if _LIST["out"] is not None and _LIST["built"] == _LIST["gen"]:
            return _LIST["out"]
        _LIST_LOCK.acquire()
    try:
        got = _list_fresh()
        if got is not None:
            return _LIST["out"]
        return _check_and_build()
    finally:
        _LIST_LOCK.release()


def list_tests_body() -> tuple[bytes, bytes]:
    """The /api/tests reply as JSON bytes and gzipped, encoded once per list (encoding the 1.25 MB list took about
    0.8 s holding the GIL, and the server did it again for every request of the team)."""
    import gzip
    out = _list_fresh_obj() or _list_checked()
    b = _BODY
    if b["of"] is out:
        return b["raw"], b["gz"]
    with _BODY_LOCK:
        if _BODY["of"] is out:
            return _BODY["raw"], _BODY["gz"]
        raw = json.dumps({"tests": out}, default=str).encode("utf-8")
        gz = gzip.compress(raw, compresslevel=5)
        _BODY.update(of=out, raw=raw, gz=gz)
        return raw, gz


def _list_fresh_obj():
    out = _LIST["out"]
    if out is not None and _LIST["key"] is not None and time.monotonic() - _LIST["at"] < LIST_FRESH:
        return out
    return None


def _check_and_build() -> list[dict]:
    from ui import store
    from ui_studio import e2e, memory
    from framework import case_loader
    gen = _LIST["gen"]
    t_check = time.monotonic()
    cases = store.list_all()
    _, with_script = e2e.catalogue()
    M = grammar.Memory()
    with state.db() as con:              # one query, not one connection per case (1,300+ cases)
        rows = con.execute("SELECT * FROM tests").fetchall()
    metas = {r["id"]: dict(r) for r in rows}
    key = (case_loader.cache_key(), e2e._cache.get("key"), memory._cache.get("stamp"),
           tuple(sorted(tuple(r) for r in rows)))
    if not (_LIST["key"] == key and _LIST["out"] is not None):
        _LIST.update(key=key, out=_build_list(cases, with_script, M, metas))
    # a save during this check: the next request checks again (this answer may not have it yet)
    _LIST.update(at=t_check if _LIST["gen"] == gen else 0.0, built=gen)
    return _LIST["out"]


def _build_list(cases, with_script, M, metas) -> list[dict]:
    from ui import store
    out = []
    for c in cases:
        d = display_id(c.id)
        meta = metas.get(d)
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
                    "draft": bool(getattr(c, "draft", False)),
                    # Studio tests: the priority chosen when saving (older YAML files always said p2)
                    "priority": (store.PRIORITY.get(str(meta["priority"] or "").lower()) if meta else None)
                    or c.priority,
                    "tags": [t for t in (c.tags or []) if t != "imported"], "scripts": len(with_script.get(c.id, [])),
                    "ver": ver_summary(c)})
    # drafts that still have red lines exist only in the database
    have = {t["id"] for t in out}
    for r in [m for m in metas.values() if m["kind"] == "draft"]:
        if r["id"] in have:
            continue
        lines = json.loads(r["lines"] or "[]")
        res, _ = grammar.parse_all(lines, M)
        out.append({"id": r["id"], "name": r["name"], "module": r["module"], "author": r["author"],
                    "date": r["created"], "type": "written", "steps": len([x for x in res if x["status"] == "ok"]),
                    "bad": sum(1 for x in res if x["status"] == "bad"), "lines": lines, "editable": True,
                    "draft": True})
    return sorted(out, key=lambda t: (t["module"], t["id"]))


_STEP_SPLIT = re.compile(r"\s*(?:->|→|=>)\s*|\s+/\s+|;\s+")


# Detailed manual steps written for cases that have none (or only a title): kept apart from the YAML, because the
# library YAML files are re-generated by framework.import_scenarios and edits there would be lost.
# {case id: {"preconditions": [...], "steps": [...], "expected": [...], "refs": [...], "checked_live": bool,
#            "written_by": "...", "updated": "dd-Mon-yyyy"}}
CASE_DETAILS = Path(__file__).resolve().parent.parent / "config" / "case_details.json"
_details_cache: dict = {"sig": None, "data": {}}


def case_details() -> dict:
    try:
        st = CASE_DETAILS.stat()
    except OSError:
        return {}
    sig = (st.st_mtime_ns, st.st_size)
    if _details_cache["sig"] != sig:
        try:
            data = json.loads(CASE_DETAILS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        _details_cache.update(sig=sig, data=data if isinstance(data, dict) else {})
    return _details_cache["data"]


def text_test(c) -> list[str]:
    """The case as plain-English steps a tester can read (and paste into the Write screen).

    Automated cases: their steps. Imported drafts: the "Manual steps" of the scenario, else the scenario
    text, else the title, split at "->", " / " and "; " the way the QA sheets write them.
    """
    if c.steps:
        return [str(s.get("note") or " ".join(str(s.get(k)) for k in ("action", "target", "value") if s.get(k)))
                for s in c.steps]
    det = case_details().get(c.id) or {}
    if det.get("steps"):
        return [str(x) for x in det["steps"]]
    pre = c.preconditions or []
    src = next((p.split(":", 1)[1] for p in pre if p.startswith("Manual steps:")), "")         or next((p.split(":", 1)[1] for p in pre if p.startswith("Scenario:")), "") or c.title
    steps = [x.strip(" .") for x in _STEP_SPLIT.split(src) if x and x.strip(" .")]
    return [x[:1].upper() + x[1:] for x in steps] or [c.title]


def case_detail(tid: str) -> dict:
    """Everything the YAML holds about one case, for the Test cases screen."""
    from ui import store
    from ui_studio import e2e
    c = store.get(yaml_id(tid))
    if not c:
        raise KeyError("test not found")
    pre = [p for p in (c.preconditions or []) if not p.startswith("DRAFT")]
    return {"id": tid, "name": c.title, "module": module_label(c.module), "priority": c.priority,
            "tags": [t for t in (c.tags or []) if t != "imported"], "destructive": bool(c.destructive),
            "draft": bool(c.draft), "expected": c.expected or [], "notes": pre,
            "steps": [" ".join(str(s.get(k)) for k in ("action", "target", "value") if s.get(k) not in (None, ""))
                      for s in c.steps], "file": c.source_file, "scripts": e2e.scripts_for_case(c.id),
            "text_steps": text_test(c), "source": next((p for p in pre if p.startswith("Source:")), ""),
            "url": case_url(c), "where": case_where(c), "verification": _ver_detail(c),
            "detail": _detail_of(c)}


def _detail_of(c) -> dict | None:
    """The written detail of a case (case_details.json), with the expected result falling back to the YAML."""
    det = case_details().get(c.id)
    if not det:
        return None
    return {"preconditions": [str(x) for x in det.get("preconditions") or []],
            "expected": [str(x) for x in det.get("expected") or []] or list(c.expected or []),
            "refs": [str(x) for x in det.get("refs") or []], "checked_live": bool(det.get("checked_live")),
            "written_by": str(det.get("written_by") or ""), "updated": str(det.get("updated") or "")}


def _ver_detail(c) -> dict | None:
    sm = ver_summary(c)
    if not sm:
        return None
    v = c.verification or {}
    shots = []
    for e in v.get("evidence") or []:
        name = Path(str(e)).name
        if name.lower().endswith(".png") and (SHOTS / name).exists():
            shots.append({"name": name, "url": f"/api/verify/shot?name={name}"})
    return {**sm, "notes": str(v.get("notes") or ""), "kb": [str(k) for k in (v.get("kb") or [])], "shots": shots,
            "files": [str(e) for e in (v.get("evidence") or [])]}


def verify_shot(name: str) -> Path:
    p = (SHOTS / Path(name).name).resolve()
    if p.parent != SHOTS.resolve() or not p.exists() or p.suffix.lower() != ".png":
        raise KeyError("screenshot not found")
    return p


def open_test(tid: str) -> dict:
    meta = _meta(tid)
    if not meta:
        raise KeyError("test not found")
    return {"id": tid, "name": meta["name"], "module": meta["module"], "author": meta["author"],
            "priority": meta["priority"] or "Medium", "description": meta["description"] or "",
            "lines": json.loads(meta["lines"] or "[]"), "code": meta["code"] or ""}


def load_cases(ids: list[str]) -> list[dict]:
    from ui import store
    from framework import test_env
    cases = []
    for disp in ids:
        c = store.get(yaml_id(disp))
        if not c:
            raise KeyError(f"{disp}: test not found or has no runnable steps")
        meta = _meta(disp)
        a, _ = _author(c)
        cases.append({"id": c.id, "display_id": disp, "name": c.title, "module": module_label(c.module),
                      "author": (meta["author"] if meta else a) or a or "unknown",
                      # made independent of what earlier tests left in the company (framework.test_env)
                      "steps": test_env.prepare_steps({"steps": c.steps, "preconditions": c.preconditions,
                                                       "verification": c.verification}),
                      "destructive": bool(c.destructive)})
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


# Saving takes the next TC number and rewrites the module's YAML file: two QAs saving at the same moment (team
# server) would get the same number and one test would overwrite the other. One save at a time.
_save_lock = threading.RLock()


def _one_at_a_time(fn):
    def wrapped(*a, **k):
        with _save_lock:
            return fn(*a, **k)
    wrapped.__name__, wrapped.__doc__ = fn.__name__, fn.__doc__
    return wrapped


def redact_code(code: str, extra_secrets: list[str] | None = None) -> str:
    """A saved script never holds a password: the recorded login becomes login(page), and any known MargBooks
    password left (a pasted script, a password typed outside the login block) becomes ***."""
    from ui_studio import recorder
    code = recorder.redact(code or "")
    if script.is_login_test(code):           # a login test keeps its login: the QA's own password -> MB_PASS
        code = recorder.redact_login_test(code, extra_secrets)
    for sec in sorted({x for x in (extra_secrets or []) if isinstance(x, str) and len(x) > 3}, key=len, reverse=True):
        code = code.replace(sec, "***")
    return code


def _remove_old_spec(old: str, new: str):
    if old and Path(old).resolve() != Path(new).resolve():
        try:
            Path(old).unlink()
        except OSError:
            pass


def _created_of(tid: str) -> str | None:
    """The date in 'Created by X | <date>' of an existing saved case, so an update keeps it."""
    from ui import store
    c = store.get(yaml_id(tid))
    return (_author(c)[1] or None) if c else None


@_one_at_a_time
def save(code: str, name: str, module: str, priority: str, description: str, author: str, source: str,
         lines: list[str] | None = None, tid: str | None = None, extra_secrets: list[str] | None = None) -> dict:
    """Save a replayed test. tid: update that test (Write > Open > ... > Save) instead of making a new one; its
    author stays the one who first wrote it."""
    from ui import store
    name, author = (name or "").strip(), (author or "").strip()
    if not module or not name or not author:
        raise ValueError("Module, test case name and Written by are required.")
    code = redact_code(code, extra_secrets)
    conv = script.to_steps(code)
    if conv["unknown"] or not conv["steps"]:
        raise ValueError("The script has lines that cannot be replayed; fix them and replay again before saving.")
    old = _meta(tid) if tid else None
    if old:
        tid, seq, author = old["id"], old["seq"], old["author"] or author
    else:
        seq = state.next_seq()
        tid = state.tc_id(seq)
    steps = _clean(conv["steps"])
    writes = any(s.get("action") in ("save_form", "set_party", "add_item", "bulk_sale_bills", "retail_bill") for s in steps)
    res = store.save(name=name, description=description, module=MODULE_YAML.get(module, module.lower().replace(" ", "_")),
                     steps=steps, author=author,
                     tags=["studio", f"priority-{(priority or 'Medium').lower()}"]
                     + (["login-test", "breaks_session"] if conv.get("login_test") else []),
                     destructive=writes, case_id=yaml_id(tid), created=_created_of(tid) if old else None,
                     priority=priority or "Medium")
    spec = _write_spec(tid, name, module, author, description, code)
    if old:
        _remove_old_spec(old["spec_file"] or "", spec)
    with state.db() as c:
        c.execute("INSERT OR REPLACE INTO tests VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tid, name, module, author, priority or "Medium", description,
                   "record" if source == "record" else "written",
                   (old["created"] if old and old["created"] else time.strftime("%d-%b-%Y")),
                   json.dumps(lines) if lines else None, code, spec, seq))
    invalidate_list()
    return {"id": tid, "yaml": res["file"], "spec": spec, "author": author, "updated": bool(old)}


@_one_at_a_time
def save_draft(tid: str | None, name: str, module: str, author: str, lines: list[str]) -> dict:
    """Write screen's 'Save draft'. Runnable (YAML written) only when every line is mapped.

    A draft of an existing test keeps what the Write screen has no place for: author, priority, description and
    created date; its .spec.ts follows the new lines."""
    from ui import store
    if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
        raise ValueError("lines must be a list of text lines.")
    lines = [ln for ln in lines if ln.strip()]
    name = name if isinstance(name, str) else ""
    if not name.strip():
        raise ValueError("Give the test case a name.")
    if not lines:
        raise ValueError("Write at least one step.")
    res, _ = grammar.parse_all(lines)
    clean = all(r["status"] != "bad" for r in res)
    old = _meta(tid) if tid else None
    if old:
        tid, seq = old["id"], old["seq"]
        author = old["author"] or author
    else:
        seq = state.next_seq()
        tid = state.tc_id(seq)
    priority = (old or {}).get("priority") or "Medium"
    description = (old or {}).get("description") or ""
    saved_before = bool(old) and old["kind"] in ("written", "record")
    code, spec = None, (old or {}).get("spec_file") or ""
    if clean:
        steps = grammar.to_steps(lines)
        writes = any(s.get("action") in ("save_form", "set_party", "add_item", "bulk_sale_bills") for s in steps)
        tags = ["studio", f"priority-{priority.lower()}"] if saved_before else ["studio", "draft-lines"]
        store.save(name=name, description=description, module=MODULE_YAML.get(module, module.lower()), steps=steps,
                   author=author, tags=tags, destructive=writes, case_id=yaml_id(tid),
                   created=_created_of(tid) if old else None, priority=priority)
        code = script.generate(name, module, author, lines, tid)["code"]
        if saved_before or spec:
            new_spec = _write_spec(tid, name, module, author, description, code)
            _remove_old_spec(spec, new_spec)
            spec = new_spec
    elif old and old["code"]:
        code = old["code"]          # red lines: the last runnable version stays as it was
    kind = "written" if clean or saved_before else "draft"
    with state.db() as c:
        c.execute("INSERT OR REPLACE INTO tests VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tid, name, module, author, priority, description, kind,
                   (old["created"] if old and old["created"] else time.strftime("%d-%b-%Y")),
                   json.dumps(lines), code, spec, seq))
    invalidate_list()
    return {"id": tid, "runnable": clean, "author": author}


def owner_of(tid: str | None) -> str | None:
    """Who wrote a saved Studio test (None: no such test)."""
    m = _meta(tid) if tid else None
    return (m["author"] or "") if m else None


# ------------------------------------------------------------------ runs

def list_runs() -> dict:
    with state.db() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY ts DESC LIMIT 300").fetchall()
    names = _user_names()
    runs = [{"id": r["id"], "test": r["test_id"], "name": r["name"], "module": r["module"], "author": r["author"],
             "at": r["at"], "passed": run_passed(dict(r)), "total": r["total"], "result": r["result"], "err": r["err"],
             "failAt": fix_fail_step(r["err"], r["fail_at"], [{}] * (r["total"] or 0))[0],
             "runBy": _run_by(r), "runByName": names.get(_run_by(r), _run_by(r))}
            for r in rows]
    p = sum(1 for r in runs if r["result"] == "Pass")
    f = sum(1 for r in runs if r["result"] == "Fail")
    return {"runs": runs, "kpis": {"runs": len(runs), "passed": p, "failed": f, "other": len(runs) - p - f,
                                    "testers": len({r["runBy"] for r in runs if r["runBy"]})}}


def _run_by(r) -> str:
    try:
        return r["run_by"] or ""
    except (IndexError, KeyError):
        return ""


def _user_names() -> dict:
    """Studio username -> display name (server mode); empty when there are no Studio accounts."""
    try:
        with state.db() as c:
            return {u["username"]: u["name"] or u["username"] for u in c.execute("SELECT username, name FROM users")}
    except Exception:  # noqa: BLE001
        return {}


def _run_row(rid: str) -> dict:
    with state.db() as c:
        r = c.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
    if not r:
        raise KeyError("run not found")
    return dict(r)


_STEP_FAILED = re.compile(r"^\s*Step (\d+) failed")


def fix_fail_step(err: str, fail_at, steps: list[dict]) -> tuple:
    """Runs saved before the step-numbering fix put the red mark on the wrong step (the error said "Step 1 failed"
    but step 11 was red). The step number in the error is the StepRunner's own: when it disagrees with the stored
    one, the failing step is that one and the steps after it did not run (they show as skipped)."""
    m = _STEP_FAILED.match(err or "")
    if not m or not steps:
        return fail_at, steps
    k = int(m.group(1)) - 1
    if not 0 <= k < len(steps) or k == fail_at:
        return fail_at, steps
    out = [dict(s) for s in steps]
    for j, s in enumerate(out):
        if j == k:
            s["status"] = "bad"
        elif j > k or s.get("status") == "bad":
            s["status"] = "skip"
    return k, out


def run_steps(r: dict) -> tuple:
    """A stored run's failing step and its steps with only finished statuses (ok / bad / skip). The executor's
    internal "doing" (a step that had started when the test ended) and "todo" are not shown to anybody: the
    failing step of a failed run is "bad", every other unfinished step is "skip". Drawer, HTML report and bug pack
    all use this, so they always agree."""
    try:
        raw = json.loads(r["steps"] or "[]")
    except (TypeError, ValueError):
        raw = []
    fail_at, steps = fix_fail_step(r["err"], r["fail_at"], raw)
    failed = str(r.get("result") or "") == "Fail"
    if failed and isinstance(fail_at, int) and 0 <= fail_at < len(steps) and not any(s.get("status") == "bad" for s in steps):
        steps = [dict(s) for s in steps]
        steps[fail_at]["status"] = "bad"
    out = []
    for s in steps:
        st = s.get("status")
        out.append({**s, "status": st if st in ("ok", "bad", "skip") else "skip"})
    return fail_at, out


def run_passed(r: dict, fixed: tuple | None = None) -> int:
    """The passed count of a stored run. When fix_fail_step moved the failing step of an old run (its steps are
    read corrected), the stored count was made from the wrong statuses: count the corrected steps instead, so
    "6/56" never stands next to a step list with no passed step."""
    stored = r.get("passed")
    if fix_fail_step(r.get("err"), r.get("fail_at"), [{}] * int(r.get("total") or 0))[0] == r.get("fail_at"):
        return stored
    fail_at, steps = fixed if fixed is not None else run_steps(r)
    return sum(1 for x in steps if x.get("status") == "ok") if steps else stored


STEP_WORD = {"ok": "ok", "bad": "FAIL", "skip": "skip"}


def run_detail(rid: str) -> dict:
    r = _run_row(rid)
    d = Path(r["dir"])
    shots = sorted(p.name for p in d.glob("*.png")) if d.exists() else []
    fail_at, steps = run_steps(r)
    return {"run": {"id": r["id"], "test": r["test_id"], "name": r["name"], "module": r["module"], "author": r["author"],
                    "at": r["at"], "passed": run_passed(r, (fail_at, steps)), "total": r["total"], "result": r["result"], "err": r["err"],
                    "failAt": fail_at, "aiFixes": r["ai_fixes"], "runBy": _run_by(r),
                    "runByName": _user_names().get(_run_by(r), _run_by(r))},
            "steps": [{"text": s["text"], "status": {"ok": "Pass", "bad": "Fail", "skip": "Skip"}.get(s["status"], "Skip")}
                      for s in steps],
            "files": {"video": (d / "run.webm").exists(), "trace": (d / "trace.zip").exists(),
                      "screens": [{"name": n, "url": f"/api/runs/file?id={rid}&name={n}"} for n in shots]},
            "explain": _explain_run(r, fail_at, steps)}


def _stored(text) -> dict:
    try:
        d = json.loads(text or "")
    except ValueError:
        return {}
    return d if isinstance(d, dict) and d.get("what") else {}


def _explain_run(r: dict, fail_at, steps: list[dict]) -> dict:
    """The failure in simple words for the drawer, the HTML report and the bug pack ({} for a pass).

    The one stored with the run is used (the AI's when a QA asked for it); a run saved before summaries were
    stored gets one now, and it is stored with it."""
    from ui_studio.explain import explain
    ai = _stored(r.get("explain_ai"))
    if ai:
        return ai | {"ai": True}
    kept = _stored(r.get("explain"))
    if kept:
        return kept
    if r["result"] == "Pass" and not r["err"]:
        return {}
    step = steps[fail_at].get("text", "") if isinstance(fail_at, int) and 0 <= fail_at < len(steps) else ""
    made = explain(r["err"] or "", step, r["result"])
    if made and r.get("id"):
        try:
            with state.db() as c:
                c.execute("UPDATE runs SET explain=? WHERE id=?", (json.dumps(made, ensure_ascii=False), r["id"]))
        except Exception:  # noqa: BLE001  (showing it matters more than keeping it)
            pass
    return made


def store_ai_explain(rid: str, summary: dict) -> None:
    """Keep the AI's explanation of a run with the run, so it is asked once and every QA sees the same."""
    if rid and summary.get("what"):
        with state.db() as c:
            c.execute("UPDATE runs SET explain_ai=? WHERE id=?", (json.dumps(summary, ensure_ascii=False), rid))


def run_file(rid: str, name: str) -> Path:
    d = Path(_run_row(rid)["dir"]).resolve()
    p = (d / Path(name).name).resolve()
    if p.parent != d or not p.exists():
        raise KeyError("file not found")
    return p


_SHOT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.png$")


def run_shot_file(rid: str, name: str) -> Path:
    """A step screenshot of a run (/api/runs/file). Only .png screenshots: the trace and video are served by
    /api/download, which scrubs the trace and sends the right content type."""
    name = str(name or "")
    if not _SHOT_NAME.match(name):
        raise KeyError("file not found")
    p = run_file(rid, name)
    if p.name != name or p.suffix != ".png":
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
    code = store.as_spec(yaml_id(disp)).get("code", "")
    if not code:
        raise KeyError("That test does not exist.")
    return code


def trace_bytes(rid: str) -> bytes:
    """A run's trace.zip without any password in it (also traces made before the Studio scrubbed them)."""
    from ui_studio import executor
    p = run_file(rid, "trace.zip")
    # scrub_trace reads the trace once per set of secrets and rewrites it only when something must go, one call
    # per file at a time, so two downloads of one trace (or a trace and a bug pack) never collide
    executor.scrub_trace(p, executor.trace_secrets(_studio_secrets()))
    return p.read_bytes()


def _studio_secrets() -> list[str]:
    """Every saved MargBooks password (server mode: each QA's own), only to scrub them out of old traces."""
    out = []
    try:
        from ui_studio import accounts
        with state.db() as c:
            rows = c.execute("SELECT mb_secret FROM users WHERE mb_secret<>''").fetchall()
        for r in rows:
            try:
                out.append(accounts.unseal(r["mb_secret"]))
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return out


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
    x = d.get("explain") or {}
    err = (f"<div style='border:1px solid #f0c2c2;background:#fdf3f3;padding:10px 14px;border-radius:8px'>"
           f"<b>{e(x['what'])}</b><p><b>Why:</b> {e(x['why'])}<br><b>What to do:</b> {e(x['next'])}<br>"
           f"<i>{e(x['side_text'])}</i></p></div>" if x else "")
    err += f"<details><summary>Technical message</summary><pre>{e(r['err'])}</pre></details>" if r["err"] else ""
    return (f"<!doctype html><meta charset='utf-8'><title>{e(r['id'])}</title><style>body{{font-family:Segoe UI,Arial;margin:24px}}"
            f"td,th{{border:1px solid #ccc;padding:6px 10px;text-align:left}}table{{border-collapse:collapse}}"
            f".Pass{{color:#14874A}}.Fail{{color:#D23A3A}}</style><h1>{e(r['id'])} · {e(r['test'])} {e(r['name'])}</h1>"
            f"<p>Module: {e(r['module'])} · Written by: <b>{e(r['author'])}</b> · Run: {e(r['at'])} · "
            f"Result: <b class='{r['result']}'>{r['result']}</b> ({r['passed']}/{r['total']})</p>{err}"
            f"<table><tr><th>#</th><th>Step</th><th>Result</th></tr>{rows}</table>")


def _run_env(r: dict) -> dict:
    """What the run used: the company its steps opened (not the Studio's active environment), the app URL, and in
    team mode who ran it with which MargBooks login."""
    from ui import envs, store
    try:
        from config.settings import settings
        e = envs.load()
        env = e["envs"].get(e.get("active")) or {}
        url = env.get("app_url") or settings.BASE_URL or ""
    except Exception:  # noqa: BLE001
        env, url = {}, ""
    company = ""
    c = store.get(yaml_id(r["test_id"] or ""))
    if c:
        company = next((str(s.get("value")).strip() for s in c.steps or []
                        if s.get("action") == "use_company" and s.get("value")), "") \
            or str((c.verification or {}).get("company") or "")
    trade, gst = _company_trade(company)
    out = {"URL": url,
           "Company": company or f"{env.get('company', '')} (the environment's company; the test does not pick one)",
           "Trade": (trade + (" (GST)" if gst else "")) if trade else ""}
    by = _run_by(r)
    if by:
        out["Run by"] = by
        try:
            with state.db() as con:
                u = con.execute("SELECT mb_user FROM users WHERE username=?", (by,)).fetchone()
            if u and u["mb_user"]:
                out["MargBooks login"] = u["mb_user"]
        except Exception:  # noqa: BLE001
            pass
    out["Run at"] = r.get("at") or ""
    return out


def bug_pack(rid: str) -> bytes:
    """One zip for developers. Never contains a password."""
    from ui import envs
    r = _run_row(rid)
    d = Path(r["dir"])
    env = _run_env(r)
    buf = io.BytesIO()
    # video, trace and screenshots are compressed already: they go in as they are (ZIP_STORED). Deflating 40-180 MB
    # of webm/zip again on every download took 40-200 s and gained nothing; the text files are still deflated.
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if (d / "run.webm").exists():
            z.write(d / "run.webm", "run.webm", compress_type=zipfile.ZIP_STORED)
        if (d / "trace.zip").exists():
            z.writestr("trace.zip", trace_bytes(rid), compress_type=zipfile.ZIP_STORED)
        for p in sorted(d.glob("*.png")) if d.exists() else []:
            z.write(p, f"screenshots/{p.name}", compress_type=zipfile.ZIP_STORED)
        try:
            z.writestr("test.spec.ts", spec_text(r["test_id"]))
            z.writestr("recorder.json", recorder_for_test(r["test_id"]))
        except KeyError:
            z.writestr("test.spec.ts", f"// {r['test_id']} no longer exists in the Studio.\n")
        fail_at, steps = run_steps(r)            # the same statuses as the drawer and the HTML report
        x = _explain_run(r, fail_at, steps)
        if x:
            z.writestr("summary.txt", f"{r['test_id']} {r['name']}: {r['result']}\n\nWhat happened: {x['what']}\n"
                                      f"Why: {x['why']}\nWhat to do: {x['next']}\n{x['side_text']}\n")
        z.writestr("steps.txt", f"{r['test_id']} {r['name']}\nWritten by: {r['author']}\n"
                   + (f"Run by: {_run_by(r)}\n" if _run_by(r) else "") + f"Result: {r['result']}\n"
                   + (f"Error: {r['err']}\n" if r["err"] else "") + "\n"
                   + "\n".join(f"{i + 1}. [{STEP_WORD[s['status']]}] {s.get('text', '')}" for i, s in enumerate(steps)))
        z.writestr("env.txt", "".join(f"{k}: {v}\n" for k, v in env.items()) + "Browser: Chromium (Playwright)\n")
        log = Path(r["dir"]) / "log.txt"                    # a Python script run's whole pytest output
        if log.exists():
            z.write(log, "log.txt")
        z.writestr("ai_fixes.txt", "AI fixes are recorded in the saved script header and the Studio AI usage log.\n")
    return buf.getvalue()
