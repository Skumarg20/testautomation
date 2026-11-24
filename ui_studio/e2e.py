"""
The Python test scripts copied from the ai-projects repo (e2e_scripts/), shown and run from Test Studio.

The scripts are pytest code with their own page objects, fixtures and settings, so they run in their own
virtualenv (e2e_scripts/.venv: Playwright < 1.64 and pytest-playwright, which must not mix with this
project's Playwright). Their settings refuse every host except premargbooks.com / localhost -- that guard
is on purpose (the scripts create bills, parties, ledgers) and is not bypassed here.

Catalogue: every test_* function in tests/journeys and tests/api, read with ast (nothing is imported),
cached until a script file changes. A script is linked to an imported YAML case when it names the
case's scenario ID (e.g. "SI-01") in its decorators, docstring or body.
"""
from __future__ import annotations

import ast
import csv
import json
import os
import re
import subprocess
import threading
import time
import uuid
from urllib.parse import urlparse
from pathlib import Path

from config.settings import ROOT

E2E = ROOT / "e2e_scripts"
PY = E2E / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MAPPING = ROOT / "testcases" / "library" / "_mapping.csv"

# journey folder -> YAML module (same names as testcases/library/*.yaml)
JOURNEY_MODULE = {
    "abha": "abha", "accounting": "accounting", "admin": "users", "auth": "auth", "banking": "banking",
    "barcode": "inventory", "cash_transfer": "accounting", "chemist": "sales", "communication_setup": "utilities",
    "company": "company", "crm": "crm", "dashboard": "dashboard", "data_sync": "utilities", "gst": "gst",
    "inventory": "inventory", "manufacturing": "manufacturing", "masters": "masters",
    "notifications_export": "utilities", "online_store": "online_store", "other_masters": "masters",
    "password_reset_registration": "auth", "print_templates": "utilities", "purchase": "purchase",
    "racks": "inventory", "reports": "reports", "returns": "purchase", "sales": "sales", "stock": "inventory",
    "subscription": "company", "support": "support", "unit_hsn": "masters",
}
SCEN_ID = re.compile(r"\b([A-Z]{1,3}-[A-Z]?\d{1,3}[a-z]?)\b")
SPEC_REF = re.compile(r"(?:specs|scenarios)/([\w-]+)\.md")
TC_ID = re.compile(r"\bTC_[A-Z]+_\d+\b")

_cache: dict = {"key": None, "scripts": [], "by_case": {}}
_lock = threading.Lock()


def available() -> bool:
    return E2E.exists() and PY.exists()


def _files() -> list[Path]:
    out = [p for p in (E2E / "tests" / "journeys").rglob("test_*.py") if not p.parent.name.startswith("zz_probe")]
    out += list((E2E / "tests" / "api").rglob("test_*.py"))
    return sorted(out)


_SPEC_ROW = re.compile(r"^\|\s*`(test_\w+)`\s*\|\s*([^|]+)\|", re.M)
_JOURNEY = re.compile(r"""journey\(\s*["']([\w-]+)["']""")


def _spec_files() -> list[Path]:
    return sorted((E2E / "specs").glob("*.md")) if (E2E / "specs").exists() else []


def _spec_ids() -> dict[tuple[str, str], list[str]]:
    """(pack, test function) -> scenario ids, from the specs' test tables ("| `test_x` | AB-01 | ... |").

    A test file often lists several ids in its docstring (AB-01, AB-32, AB-02, AB-03) while each function covers one;
    the spec says which function is which, so a case links to the right function."""
    out: dict[tuple[str, str], list[str]] = {}
    for f in _spec_files():
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for fn, cell in _SPEC_ROW.findall(text):
            ids = SCEN_ID.findall(cell)
            if ids:
                out.setdefault((f.stem, fn), [])
                out[(f.stem, fn)] += [i for i in ids if i not in out[(f.stem, fn)]]
    return out


def _module_of(path: Path) -> str:
    parts = path.relative_to(E2E / "tests").parts
    if parts[0] == "api":
        return "api"
    return JOURNEY_MODULE.get(parts[1], parts[1])


def _skipped(node: ast.AST, src: str) -> bool:
    deco = " ".join(ast.get_source_segment(src, d) or "" for d in getattr(node, "decorator_list", []))
    return bool(re.search(r"mark\.skip\b|mark\.skip\(|mark\.skipif\(", deco))


def _title(fn: ast.FunctionDef) -> str:
    doc = ast.get_docstring(fn)
    if doc:
        return doc.strip().split("\n")[0].rstrip(".")
    words = fn.name.removeprefix("test_").replace("_", " ")
    return words[:1].upper() + words[1:]


# The QA Excel sheets behind scenarios/manual-sale-purchase.md: the scripts cite "Row 45", the imported
# cases are AJ-045 (Ajay sheet) or SC-045 (sale checklist). Which sheet is named in the file's docstring;
# a file that names both, or neither, is not linked by row.
_SHEETS = (("SC", re.compile(r"sale checklist", re.I)), ("AJ", re.compile(r"\bajay\b", re.I)))
_ROWS = re.compile(r"\b[Rr]ows?\s+(\d{1,3}(?:\s*(?:,|and|-|–|to)\s*\d{1,3})*)")


def _sheet_of(doc: str) -> str:
    named = [prefix for prefix, pat in _SHEETS if pat.search(doc)]
    return named[0] if len(named) == 1 else ""


def _sheet_row_ids(text: str, sheet: str) -> list[str]:
    if not sheet:
        return []
    out = []
    for group in _ROWS.findall(text):
        for a, b in re.findall(r"(\d{1,3})(?:\s*(?:-|–|to)\s*(\d{1,3}))?", group):
            lo, hi = int(a), int(b or a)
            if hi - lo <= 20:
                out += [f"{sheet}-{n:03d}" for n in range(lo, hi + 1)]
    return out


def _read_file(path: Path, spec_ids: dict | None = None) -> list[dict]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    rel = path.relative_to(E2E).as_posix()
    module = _module_of(path)
    doc = ast.get_docstring(tree) or ""
    packs = sorted(set(SPEC_REF.findall(doc)))
    sheet = _sheet_of(doc)
    file_skip = bool(re.search(r"pytestmark\s*=.*mark\.skip", src))
    prio = (re.search(r"pytest\.mark\.(p[0-3])\b", src) or [None, ""])[1]
    lines = src.split("\n")
    out = []
    journeys = sorted(set(_JOURNEY.findall(src)) | set(packs))     # the scenario pack(s) this file belongs to
    spec_ids = spec_ids or {}

    def add(fn: ast.FunctionDef, cls: str = "", cls_skip: bool = False):
        start = min([d.lineno for d in fn.decorator_list] + [fn.lineno])
        text = "\n".join(lines[start - 1:fn.end_lineno])
        ids = sorted(set(SCEN_ID.findall(text)) | set(_sheet_row_ids(text, sheet))
                     | {i for j in journeys for i in spec_ids.get((j, fn.name), [])})
        tc_ids = sorted(set(TC_ID.findall(text + "\n" + doc)))
        params = text.count("pytest.param(")
        out.append({"node": f"{rel}::{cls + '::' if cls else ''}{fn.name}", "file": rel, "func": fn.name,
                    "title": _title(fn), "module": module, "ids": ids, "tc_ids": tc_ids, "packs": packs, "priority": prio,
                    "params": params, "skipped": file_skip or cls_skip or _skipped(fn, src),
                    "doc": (ast.get_docstring(fn) or "").strip(), "file_doc": doc.strip().split("\n\n")[0]})

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            add(node)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name.startswith("test_"):
                    add(sub, node.name, _skipped(node, src))
    return out


def _mapping() -> list[dict]:
    if not MAPPING.exists():
        return []
    with open(MAPPING, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _resolve(sid: str, s: dict, by_src: dict[str, list[dict]]) -> str:
    """Scenario ID -> imported case id. An ID used by several packs goes to the pack the script file names
    (specs/<pack>.md), else to the pack of the same module, else to the only pack that has it; never a guess."""
    rows = by_src.get(sid, [])
    pick = [r for r in rows if r["source_pack"].removesuffix(".md") in s["packs"]] \
        or [r for r in rows if r["module"] == s["module"]] or rows
    return pick[0]["new_id"] if len(pick) == 1 else ""


def _variants() -> dict[str, list[str]]:
    """Function node -> its parameter ids, as pytest collects them.

    Many scripts are one function run over a data file (document_cases.json, outstanding_cases.py), so
    the scenario IDs (CON-001, OA-061) exist only in the collected names: test_x[chromium-OA-061]."""
    if not PY.exists():
        return {}
    try:
        p = subprocess.run([str(PY), "-m", "pytest", "tests/journeys", "tests/api", "--collect-only", "-q",
                            "-p", "no:cacheprovider", "-o", "addopts="], cwd=str(E2E), env=script_env(),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:  # noqa: BLE001  (no variants is fine: functions are still listed and linked)
        return {}
    out: dict[str, list[str]] = {}
    for line in p.stdout.splitlines():
        m = re.fullmatch(r"(tests/\S+?)\[(.+)\]", line.strip())
        if m:
            out.setdefault(m.group(1), []).append(m.group(2))
    return out


def _link(scripts: list[dict], variants: dict[str, list[str]]) -> dict[str, list[str]]:
    """YAML case id -> script nodes: the function node, or one variant node (test_x[chromium-OA-061])."""
    by_src: dict[str, list[dict]] = {}
    for r in _mapping():
        by_src.setdefault(r["source_id"], []).append(r)
    by_case: dict[str, list[str]] = {}

    def add(s: dict, case: str, node: str):
        if case not in s["cases"]:
            s["cases"].append(case)
        if node not in by_case.setdefault(case, []):
            by_case[case].append(node)

    for s in scripts:
        s["cases"] = []
        s["variants"] = variants.get(s["node"], [])
        for tc in s["tc_ids"]:                  # a script that names the case itself (Studio-started ones)
            add(s, tc, s["node"])
        for sid in s["ids"]:
            case = _resolve(sid, s, by_src)
            if case:
                add(s, case, s["node"])
        for param in s["variants"]:
            for sid in SCEN_ID.findall(param):
                case = _resolve(sid, s, by_src)
                if case:
                    add(s, case, f"{s['node']}[{param}]")
    return by_case


def catalogue() -> tuple[list[dict], dict[str, list[str]]]:
    if not E2E.exists():
        return [], {}
    files = _files()
    data = list((E2E / "test_data").glob("*")) if (E2E / "test_data").exists() else []
    specs = _spec_files()
    key = (len(files), max((f.stat().st_mtime for f in files + data + specs), default=0), len(specs),
           MAPPING.stat().st_mtime if MAPPING.exists() else 0)
    with _lock:
        if _cache["key"] != key:
            got = _disk_load(key)
            if got:
                _cache.update(key=key, scripts=got[0], by_case=got[1])
            else:
                sids = _spec_ids()
                scripts = [s for f in files for s in _read_file(f, sids)]
                _cache.update(key=key, scripts=scripts, by_case=_link(scripts, _variants()))
                _disk_save(key, _cache["scripts"], _cache["by_case"])
        return _cache["scripts"], _cache["by_case"]


_DISK = Path(__file__).resolve().parents[1] / "artifacts" / ".cache" / "e2e_catalogue.pkl"


def _disk_load(key):
    import pickle
    try:
        with open(_DISK, "rb") as fh:
            k, scripts, by_case = pickle.load(fh)
        return (scripts, by_case) if k == key else None
    except Exception:  # noqa: BLE001
        return None


def _disk_save(key, scripts, by_case) -> None:
    import os, pickle
    try:
        _DISK.parent.mkdir(parents=True, exist_ok=True)
        tmp = _DISK.with_suffix(".tmp")
        with open(tmp, "wb") as fh:
            pickle.dump((key, scripts, by_case), fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, _DISK)
    except Exception:  # noqa: BLE001
        pass


def list_scripts(module_yaml: str = "") -> list[dict]:
    scripts, _ = catalogue()
    from ui_studio.tests import module_label
    keep = ("node", "file", "title", "module", "ids", "cases", "priority", "skipped")
    return [{k: s[k] for k in keep} | {"label": "API" if s["module"] == "api" else module_label(s["module"]),
                                       "params": max(s["params"], len(s.get("variants", [])))}
            for s in scripts if not module_yaml or s["module"] == module_yaml]


def _base(node: str) -> str:
    return node.split("[", 1)[0]


def script_detail(node: str) -> dict:
    """A catalogue function, also when asked by one of its variants (test_x[chromium-OA-061])."""
    scripts, _ = catalogue()
    base = _base(node)
    for s in scripts:
        if s["node"] == base and (node == base or node[len(base) + 1:-1] in s.get("variants", [])):
            return s
    raise KeyError("script not found")


def scripts_for_case(case_id: str) -> list[dict]:
    scripts, by_case = catalogue()
    by_node = {s["node"]: s for s in scripts}
    out = []
    for node in by_case.get(case_id, []):
        s = by_node.get(_base(node))
        if s:
            variant = node[len(s["node"]):]
            out.append({"node": node, "title": s["title"] + (f" {variant}" if variant else ""), "skipped": s["skipped"]})
    return out


# ------------------------------------------------------------------ view / edit

BACKUPS = E2E / "results" / "studio-backups"


def _file_of(node: str) -> tuple[Path, dict]:
    """The script file of a catalogue node. Only catalogued test files, never a path from the request."""
    s = script_detail(node)
    path = (E2E / s["file"]).resolve()
    if path not in {f.resolve() for f in _files()}:
        raise KeyError("script not found")
    return path, s


def _fn_lines(path: Path, node: str) -> tuple[int, int]:
    """First (decorators included) and last line of the test in the file, 1-based."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = _base(node).split("::")[1:]
    body = tree.body
    for name in names[:-1]:
        body = next((n.body for n in body if isinstance(n, ast.ClassDef) and n.name == name), [])
    fn = next((n for n in body if isinstance(n, ast.FunctionDef) and n.name == names[-1]), None)
    if not fn:
        return 0, 0
    return min([d.lineno for d in fn.decorator_list] + [fn.lineno]), fn.end_lineno


def _digest(raw: bytes) -> str:
    import hashlib
    return hashlib.sha256(raw).hexdigest()[:16]


def source(node: str) -> dict:
    path, s = _file_of(node)
    raw = path.read_bytes()
    start, end = _fn_lines(path, node)
    return {"node": node, "file": s["file"], "text": raw.decode("utf-8").replace("\r\n", "\n"),
            "start": start, "end": end, "hash": _digest(raw)}


def save(node: str, text: str, digest: str) -> dict:
    """Write the edited file back. Refused when it is not valid Python or changed on disk since it was opened."""
    path, s = _file_of(node)
    raw = path.read_bytes()
    if _digest(raw) != digest:
        raise ValueError("This file was changed by someone else after you opened it. Close, open it again and "
                         "redo your change.")
    text = text.replace("\r\n", "\n")
    try:
        ast.parse(text)
    except SyntaxError as e:
        raise ValueError(f"Not saved: Python syntax error on line {e.lineno}: {e.msg}") from None
    if not text.endswith("\n"):
        text += "\n"
    if b"\r\n" in raw:
        text = text.replace("\n", "\r\n")
    BACKUPS.mkdir(parents=True, exist_ok=True)
    (BACKUPS / f"{time.strftime('%Y%m%d-%H%M%S')}_{path.name}").write_bytes(raw)
    path.write_bytes(text.encode("utf-8"))
    out = source(node) if _fn_lines(path, node) != (0, 0) else {"node": node, "file": s["file"], "start": 0, "end": 0,
                                                                "hash": _digest(path.read_bytes())}
    return out | {"saved": True}


# ------------------------------------------------------------------ new script for a case

def _journey_dir(module_yaml: str) -> Path:
    """The journey folder that already holds most scripts of this module (sales -> tests/journeys/sales)."""
    scripts, _ = catalogue()
    counts: dict[str, int] = {}
    for s in scripts:
        if s["module"] == module_yaml and s["file"].startswith("tests/journeys/"):
            top = s["file"].split("/")[2]
            counts[top] = counts.get(top, 0) + 1
    if not counts:
        raise ValueError(f"No script folder for the module '{module_yaml}' yet, so a script cannot be started here.")
    return E2E / "tests" / "journeys" / max(counts, key=counts.get)


def _pytestmark(folder: Path) -> str:
    """p2 plus the journey most scripts in this folder belong to (their markers are strict and feed the
    coverage matrix). Groups such as xdist_group are not copied: they are about what a test does."""
    counts: dict[str, int] = {}
    for f in folder.rglob("test_*.py"):
        for j in re.findall(r"pytest\.mark\.journey\(\s*['\"]([\w-]+)['\"]", f.read_text(encoding="utf-8")):
            counts[j] = counts.get(j, 0) + 1
    if not counts:
        return "pytestmark = [pytest.mark.p2]"
    return f'pytestmark = [pytest.mark.p2, pytest.mark.journey("{max(counts, key=counts.get)}")]'


WRITING: dict[str, dict] = {}                 # "Write as a script" jobs: AI takes up to a few minutes


def new_script_start(case_id: str, who: str = "") -> dict:
    """Start writing a case's script in the background (the screen shows its stage). One job per case: a second
    click joins the job that is running. A case that already has a script just opens it."""
    from ui import store
    from ui_studio import tests
    c = store.get(tests.yaml_id(case_id))
    if not c:
        raise KeyError("test not found")
    existing = scripts_for_case(c.id)
    if existing:
        return {"job": "", "state": "done", "result": {"node": existing[0]["node"], "created": False}}
    running = next((j for j in WRITING.values() if j["case"] == c.id and j["state"] == "running"), None)
    if running:
        return {"job": running["id"]}
    jid = uuid.uuid4().hex[:8]
    job = {"id": jid, "case": c.id, "state": "running", "stage": "Starting…", "step": 0, "t0": time.time(),
           "result": None, "error": ""}
    WRITING[jid] = job

    def work():
        try:
            job["result"] = new_script(c.id, lambda stage, step: job.update(stage=stage, step=step))
            if job["result"].get("created"):              # who wrote which script: the admin's Team view
                from ui_studio import team
                team.log(who, "script_written", c.id, job["result"]["node"] + (" (AI)" if job["result"].get("ai")
                                                                            else " (starting point)"))
            job["state"] = "done"
        except Exception as e:  # noqa: BLE001
            job.update(state="error", error=str(e) or type(e).__name__)
        job["secs"] = round(time.time() - job["t0"], 1)

    threading.Thread(target=work, daemon=True).start()
    return {"job": jid}


def new_script_status(jid: str) -> dict:
    j = WRITING.get(jid)
    if not j:
        raise KeyError("script writing not found")
    return {"state": j["state"], "stage": j["stage"], "step": j["step"], "steps": 4, "case": j["case"],
            "elapsed": round(time.time() - j["t0"], 1), "result": j["result"], "error": j["error"]}


def _slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:10]
    return "_".join(words) or "case"


def new_script(case_id: str, progress=None) -> dict:
    """Start a script for a test case that has none: a skipped test with the case's steps as comments.

    Lands next to the module's other scripts as test_studio_<case>.py and names the scenario ID, so the
    catalogue links it back to the case. Never overwrites a file.
    """
    from ui import store
    from ui_studio import tests
    c = store.get(tests.yaml_id(case_id))
    if not c:
        raise KeyError("test not found")
    existing = scripts_for_case(c.id)
    if existing:
        return {"node": existing[0]["node"], "created": False}
    folder = _journey_dir(c.module)
    path = folder / f"test_studio_{c.id.lower()}.py"
    if path.exists():
        raise ValueError(f"{path.relative_to(E2E).as_posix()} already exists. Open it from the Scripts tab.")
    src = next((p for p in (c.preconditions or []) if p.startswith("Source:")), "")
    m = re.search(r"scenarios/([\w-]+\.md) (\S+)", src)
    pack, sid = (m.group(1), m.group(2)) if m else ("", "")
    ref = f"Scenario: scenarios/{pack} {sid}. " if pack else ""
    fn = f"test_{_slug(c.title)}"
    # First: a real test written by the AI from the case's detailed steps and the journey's own fixtures and page
    # objects, checked (static checks + pytest --collect-only) before it is kept. Else the skeleton below.
    why = ""
    if not os.environ.get("STUDIO_NO_AI_SCRIPTS"):
        from ui_studio import script_writer
        try:
            got = script_writer.write(c, folder, path, fn, _pytestmark(folder), sid, pack, progress)
        except Exception as e:  # noqa: BLE001  (AI off / no key / limit / provider error)
            got = {"ok": False, "notes": [(str(e) or type(e).__name__)[:300]], "tokens": 0}
        if got["ok"]:
            _cache["key"] = None
            return {"node": f"{path.relative_to(E2E).as_posix()}::{fn}", "created": True, "ai": True,
                    "notes": got["notes"], "tokens": got.get("tokens", 0)}
        why = "; ".join(got["notes"])[:600]
    steps = "\n".join(f"    # {i}. {x}" for i, x in enumerate(tests.text_test(c), 1))
    det = tests.case_details().get(c.id) or {}
    expected = "\n".join(f"    # - {x}" for x in (det.get("expected") or c.expected or [])) \
        or "    # - (not written in the scenario)"
    title = c.title.replace('"""', "'''").replace("\\", "/")
    body = (f'"""{title} (started in Test Studio).\n\n{ref}Test case: {c.id}.\n"""\n\n'
            f"import pytest\n\n{_pytestmark(folder)}\n\n\n"
            f"def {fn}() -> None:\n"
            f'    """{title}."""\n'
            f"    # Steps:\n{steps}\n"
            f"    # Expected:\n{expected}\n"
            f'    pytest.skip("{sid or c.id}: not written yet. Replace this line with the steps, using the page_as / '
            f'data fixtures (see README.md).")\n')
    ast.parse(body)
    path.write_text(body, encoding="utf-8")
    return {"node": f"{path.relative_to(E2E).as_posix()}::{fn}", "created": True, "ai": False,
            "notes": [f"Only a starting point was written (the steps as comments): {why}"] if why else []}


# ------------------------------------------------------------------ run

JOBS: dict[str, dict] = {}
_run_lock = threading.Lock()


def setup_problem() -> str:
    if not E2E.exists():
        return "The e2e_scripts folder is missing."
    if not PY.exists():
        return ("The scripts' own Python environment is missing. In e2e_scripts run: python -m venv .venv, "
                "then install its packages (see e2e_scripts/README-STUDIO.md).")
    return ""                       # URL, login and company come from Test Studio's Settings (studio_env)


def _env_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {m.group(1) for m in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", path.read_text(encoding="utf-8"), re.M)}


def script_env() -> dict:
    """The environment a script runs with: this project's own settings removed.

    The Studio process has loaded this project's .env (MARGBOOKS_LOGIN_URL=accounts.margbooks.com,
    the books5 login...). The scripts read the same names, so passing them on would point a script at
    production; their guard refuses that, but they must not see these values at all. Each script gets
    only what e2e_scripts/.env gives it.
    """
    drop = _env_keys(ROOT / ".env") | _env_keys(ROOT / ".env.example") | _env_keys(E2E / ".env.example")
    env = {k: v for k, v in os.environ.items()
           if k not in drop and not k.startswith(("MARGBOOKS_", "QA_", "MB_"))}
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return env


COMPANY_MAP = ROOT / "config" / "e2e_company_map.json"
DEFAULT_COMPANY_MAP = {"Pharma New Company 23-09": "QA Chemist", "Garments New 29-08": "QA Garment",
                       "General Billing 13_10": "QA Billing General"}


def company_map() -> dict[str, str]:
    """The companies the scripts were written for (on premargbooks) -> the QA test company each runs in here."""
    try:
        m = json.loads(COMPANY_MAP.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in m.items() if not str(k).startswith("_")} or dict(DEFAULT_COMPANY_MAP)
    except (OSError, ValueError):
        return dict(DEFAULT_COMPANY_MAP)


def studio_env(owner: dict | None = None) -> dict:
    """What a script runs against: the environment, login and company of Test Studio's Settings, with the QA guard.

    The scripts' own .env (premargbooks) is overridden: environment variables win over it. Writes are allowed only
    in the QA test companies (their ids from the app's company list), and none at all when Settings has
    "Allow tests that create or change data" off."""
    from ui import envs
    from framework.qa_company import TEST_COMPANIES
    from ui_studio import qa_ids
    e = envs.apply_active() or {}
    app_url = str(e.get("app_url") or "").rstrip("/")
    login_url = str(e.get("login_url") or f"{app_url}/login")
    if not app_url:
        raise ValueError("Settings > App under test has no MargBooks URL.")
    user = (owner or {}).get("mb_user") or e.get("user") or ""
    password = (owner or {}).get("mb_password") or e.get("password") or ""
    if not (user and password):
        raise ValueError("Settings > App under test has no MargBooks login.")
    known = qa_ids.get(app_url)                       # also learns where the login page really is
    ids = known if e.get("allow_writes") else {}
    login_url = qa_ids.login_page(app_url) or login_url
    company = str(e.get("company") or "").split(" (")[0].strip()
    default = company if company in TEST_COMPANIES else "QA Chemist"
    hosts = {(urlparse(u).hostname or "").lower() for u in (app_url, login_url)} - {""}
    env = {"STUDIO_QA_GUARD": "1", "STUDIO_TARGET_HOSTS": ",".join(sorted(hosts)),
           "STUDIO_QA_COMPLINKIDS": ",".join(sorted(ids.values())),
           "STUDIO_COMPANY_MAP": json.dumps(company_map()), "STUDIO_DEFAULT_COMPANY": default,
           "MARGBOOKS_QA_URL": app_url, "MARGBOOKS_LOGIN_URL": login_url, "MARGBOOKS_API_URL": "",
           "LOGIN_STYLE": "two_step", "QA_POOL": "{}"}
    for acc in ("CHEMIST", "PHARMA", "RETAIL", "GROCERY", "GARMENTS", "ADMIN", "OPERATOR", "ACCOUNTANT"):
        env[f"QA_{acc}_USER"], env[f"QA_{acc}_PASS"] = user, password
    env["QA_GARMENTS_ALT_USER"] = ""
    return env


def start(node: str, headed: bool = False, owner: dict | None = None, who: str = "") -> dict:
    script_detail(node)                       # only nodes from the catalogue, never free text
    why = setup_problem()
    if why:
        raise ValueError(why)
    if any(j["state"] == "running" for j in JOBS.values()):
        raise ValueError("A script is already running. Wait for it to finish.")
    jid = uuid.uuid4().hex[:8]
    argv = [str(PY), "-m", "pytest", node, "-p", "no:cacheprovider", "-n", "0", "--tb=short"]
    from ui_studio import mode
    if headed and not mode.SERVER:            # on the team server a window would open on the server, unseen
        argv.append("--headed")
    from ui_studio import executor
    job = {"id": jid, "node": node, "state": "running", "log": [], "t0": time.time(), "secs": 0, "summary": "",
           "_owner": owner, "title": node, "dir": str(executor.RUNS_DIR / f"script_{jid}"), "run_id": "",
           "who": who}
    JOBS[jid] = job
    threading.Thread(target=_run, args=(job, argv), daemon=True).start()
    return {"job": jid}


def _run(job: dict, argv: list[str]):
    from ui_studio import executor
    with _run_lock, executor._slot(job, {"steps": []}):   # waits like a Studio run: one browser per login
        try:
            job["log"].append("Test Studio mode: environment, login and company from Settings; writes only in the "
                              "QA test companies.")
            env = {**script_env(), **studio_env(job.get("_owner")),
                   "STUDIO_LIVE_DIR": job["dir"], "QA_RECORD": "1"}   # live steps + screenshots, and the video
            if not env["STUDIO_QA_COMPLINKIDS"]:
                job["log"].append("Writes are off for this run (Settings > Allow tests that create or change data "
                                  "is off): any save is refused.")
            p = subprocess.Popen(argv, cwd=str(E2E), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for raw in p.stdout:
                job["log"].append(raw.decode("utf-8", "replace").rstrip())
                del job["log"][:-400]
            rc = p.wait()
        except Exception as e:  # noqa: BLE001
            job["log"].append(f"Could not start the script: {e}")
            rc = -1
    summary = next((ln.strip("= ") for ln in reversed(job["log"]) if re.search(r"\b(passed|failed|skipped|error)", ln)
                    and " in " in ln), "")
    job["summary"] = summary
    job["hint"] = explain(job["log"])
    job["secs"] = round(time.time() - job["t0"], 1)
    if rc == 0:
        job["state"] = "skipped" if "skipped" in summary and "passed" not in summary else "passed"
    elif rc == 5:
        job["state"] = "skipped"
    else:
        job["state"] = "failed"
    try:
        _keep_video(job)
        Path(job["dir"]).mkdir(parents=True, exist_ok=True)           # the whole pytest output, kept with the run
        (Path(job["dir"]) / "log.txt").write_text("\n".join(job["log"]) + "\n", encoding="utf-8")
        job["run_id"] = _save_script_run(job)
    except Exception as e:  # noqa: BLE001  (the run itself is over; only its report could not be kept)
        job["log"].append(f"The run could not be added to Reports: {e}")


# What a script's log means, in words a QA can act on (the cause is often the setup, not the test).
_EXPLAIN = [
    (re.compile(r"\[studio-guard\] BLOCKED", re.I),
     "The QA guard stopped a save, change or delete: the script tried to write outside the QA test companies (or a "
     "Control Room setting save, or writes are off in Settings). Nothing was written. The [studio-guard] line above "
     "says which request."),
    (re.compile(r'waiting for locator\("input#password"\) to be visible|Registered Mobile No\. Or Email Id', re.I),
     "The script could not log in with the MargBooks login of Settings > App under test (the password step never "
     "came). Check it with Settings > Test login. The test itself was not reached."),
    (re.compile(r"MissingCredentialsError|has no credentials|not provided; tests skip", re.I),
     "There is no MargBooks login in Settings > App under test (team mode: Settings > My MargBooks login)."),
    (re.compile(r"must be an allowed non-production host", re.I),
     "The script refused the environment's address. Check Settings > App under test (URL and login URL)."),
    (re.compile(r"Could not read the QA test companies' ids", re.I),
     "The QA test companies could not be found with this login, so the script could not be started safely. Check "
     "Settings > App under test (Test login)."),
    (re.compile(r"ABHA precondition|AB-0?2 precondition", re.I),
     "Skipped on purpose: the company does not meet the ABHA precondition (a chemist company with Control Room "
     "field 4426 filled, or blank for AB-02). See the skip reason above."),
    (re.compile(r"net::ERR_|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION", re.I),
     "The browser could not reach the site: check the network / VPN and MARGBOOKS_QA_URL in e2e_scripts/.env."),
]


def explain(log: list[str]) -> str:
    text = "\n".join(log[-400:])
    return next((msg for pat, msg in _EXPLAIN if pat.search(text)), "")


def current() -> dict:
    """The script run that is going now ({} when none): the Run screen follows it after a reload."""
    j = next((j for j in JOBS.values() if j.get("state") == "running"), None)
    return {"job": j["id"], "node": j["node"]} if j else {}


def live_steps(job: dict) -> list[dict]:
    """The steps the script has done so far (e2e_scripts/plugins/studio_live.py writes them as it goes)."""
    f = Path(job.get("dir") or "") / "steps.jsonl"
    out = []
    try:
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                s = json.loads(ln)
            except ValueError:
                continue
            out.append({"text": str(s.get("text") or "")[:200], "status": "ok" if s.get("status") == "ok" else "bad",
                        "secs": s.get("secs"), "shot": s.get("shot") or None, "error": s.get("error") or ""})
    except OSError:
        pass
    return out


def _keep_video(job: dict) -> None:
    """QA_RECORD=1 left the run's video under e2e_scripts/results/recordings: keep it with the run as run.webm."""
    vids = [v for v in (E2E / "results" / "recordings").rglob("*.webm") if v.stat().st_mtime >= job["t0"] - 1]
    if vids:
        import shutil
        Path(job["dir"]).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(max(vids, key=lambda v: v.stat().st_size), Path(job["dir"]) / "run.webm")


def _save_script_run(job: dict) -> str:
    """The script's run in Reports, like a Studio run: its steps, a screenshot per step, the video."""
    from ui_studio import executor, tests
    steps = live_steps(job)
    s = next((x for x in catalogue()[0] if x["node"] == _base(job["node"])), {})
    case_id = (s.get("cases") or [""])[0]
    err = ""
    if job["state"] != "passed":
        err = next((ln.strip()[2:].strip() for ln in job["log"] if ln.startswith("E ") and ln[2:].strip()
                    and not ln[2:].strip().startswith(("-", "+"))), "") or job.get("summary", "")
        err = ((job.get("hint") + " | ") if job.get("hint") else "") + err
    fail = next((i for i, x in enumerate(steps) if x["status"] == "bad"), -1)
    outcome = {"passed": "passed", "skipped": "skipped"}.get(job["state"], "failed")
    c = {"display_id": case_id or s.get("func", job["node"].split("::")[-1]), "id": "",
         "name": (s.get("title") or job["node"].split("::")[-1]) + " (Python script)",
         "module": tests.module_label(s.get("module", "")) if s.get("module") else "", "author": "Python script"}
    res = {"outcome": outcome, "error": err[:1500], "failed_step": fail}
    row = ([{"text": x["text"], "status": x["status"], "secs": x["secs"], "shot": x["shot"]} for x in steps]
           or [{"text": job["node"].split("::")[-1], "status": "ok" if outcome == "passed" else "bad",
                "secs": job["secs"]}])
    run_job = {"dir": job["dir"], "_owner": job.get("_owner"), "who": job.get("who", "")}
    return executor._save_run(run_job, c, res, row, sum(1 for x in row if x["status"] == "ok"))["run_id"]


def _explain_job(j: dict, steps: list[dict]) -> dict:
    """A finished script run that did not pass, in simple words (the failing step and the log's error)."""
    if j.get("state") in ("running", "passed"):
        return {}
    from ui_studio.explain import explain
    bad = next((s for s in steps if s["status"] != "ok"), None)
    err = "\n".join(ln for ln in j["log"] if ln.startswith("E ") or "[studio-guard]" in ln or "SKIPPED" in ln)[-3000:]
    err = ((bad["error"] + "\n") if bad and bad.get("error") else "") + err
    return explain(err, bad["text"] if bad else "", j.get("state", ""))


def shot_file(jid: str, name: str) -> Path:
    j = JOBS.get(jid)
    if not j or not re.fullmatch(r"step\d{3}\.png", str(name or "")):
        raise KeyError("file not found")
    p = Path(j["dir"]) / name
    if not p.exists():
        raise KeyError("file not found")
    return p


def status(jid: str) -> dict:
    j = JOBS.get(jid)
    if not j:
        raise KeyError("script run not found")
    steps = live_steps(j)
    return {k: j[k] for k in ("id", "node", "state", "summary", "secs")} | {"hint": j.get("hint", ""),
        "steps": steps, "shot": next((s["shot"] for s in reversed(steps) if s["shot"]), None),
        "run_id": j.get("run_id", ""), "waiting": j.get("waiting", ""), "explain": _explain_job(j, steps),
        "log": "\n".join(j["log"][-200:]), "elapsed": round(time.time() - j["t0"], 1)}
