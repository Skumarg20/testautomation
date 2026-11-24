"""
"Write as a script": write a real pytest-playwright test for a test case, in the style of e2e_scripts.

The AI gets only what the project already has, read from the files (nothing is imported):
  * the case: title, detailed steps / before-you-start / expected (config/case_details.json), scenario row;
  * the journey's fixtures (conftest.py chain) with their return types;
  * the page objects its tests use, with every public method and its first docstring line;
  * one sibling test of the same journey as the style example, and the spec lines about the scenario.
Then the code is checked before it is saved:
  1. it parses, has exactly the module markers and one or more test_ functions;
  2. every test argument is a known fixture, every `Class(...)`/fixture object method it calls exists;
  3. `pytest --collect-only` in the scripts' own environment collects it (imports and markers are right).
A failed check goes back to the AI once with the error. If it still fails, or AI is off, the old skeleton is
written instead (a skipped test with the steps as comments), with the reason.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

from ui_studio import e2e, state

PYTEST_BUILTIN_FIXTURES = {"page", "context", "browser", "browser_name", "browser_context_args", "base_url",
                           "request", "tmp_path", "monkeypatch", "capsys", "playwright", "is_chromium",
                           "browser_type", "launch_browser", "new_context"}
MAX_CTX = 60_000


# ------------------------------------------------------------------ reading the project (ast only)

def _parse(path: Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None


def _conftests(folder: Path) -> list[Path]:
    out, p = [], folder
    while True:
        if (p / "conftest.py").exists():
            out.append(p / "conftest.py")
        if p == e2e.E2E or e2e.E2E not in p.parents:
            break
        p = p.parent
    return out[::-1]


def fixtures_of(folder: Path) -> dict[str, str]:
    """fixture name -> 'name(args) -> Type: first doc line' for the journey folder and every conftest above it."""
    out: dict[str, str] = {}
    for cf in _conftests(folder):
        tree = _parse(cf)
        for node in (tree.body if tree else []):
            if isinstance(node, ast.FunctionDef) and any("fixture" in ast.unparse(d) for d in node.decorator_list):
                ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                doc = (ast.get_docstring(node) or "").strip().split("\n")[0]
                args = ", ".join(a.arg for a in node.args.args)
                out[node.name] = f"{node.name}({args}){ret}" + (f": {doc}" if doc else "")
    return out


def _module_file(mod: str) -> Path | None:
    p = e2e.E2E.joinpath(*mod.split("."))
    if p.with_suffix(".py").exists():
        return p.with_suffix(".py")
    if (p / "__init__.py").exists():
        return p / "__init__.py"
    return None


def classes_in(path: Path) -> dict[str, ast.ClassDef]:
    tree = _parse(path)
    return {n.name: n for n in (tree.body if tree else []) if isinstance(n, ast.ClassDef)}


def _imports(tree) -> dict[str, str]:
    """imported name -> module, for `from pages.x import A, B` (pages.*, fixtures.*, test_data.*, config.*)."""
    out = {}
    for n in ast.walk(tree) if tree else []:
        if isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in ("pages", "fixtures", "test_data", "config"):
            for a in n.names:
                out[a.asname or a.name] = n.module
    return out


def class_methods(name: str, module: str, seen: set | None = None) -> dict[str, str]:
    """method name -> 'name(args): doc' of a project class, its bases inside the project included."""
    seen = seen or set()
    if (name, module) in seen:
        return {}
    seen.add((name, module))
    f = _module_file(module)
    cls = classes_in(f).get(name) if f else None
    if not cls:
        return {}
    out: dict[str, str] = {}
    imports = _imports(_parse(f))
    for b in cls.bases:
        bname = ast.unparse(b).split(".")[-1]
        bmod = imports.get(bname) or (module if bname in classes_in(f) else None)
        if bmod:
            out.update(class_methods(bname, bmod, seen))
    for n in cls.body:
        if isinstance(n, ast.FunctionDef) and (not n.name.startswith("_") or n.name == "__init__"):
            args = ", ".join(a.arg for a in n.args.args[1:])
            doc = (ast.get_docstring(n) or "").strip().split("\n")[0]
            out[n.name] = f"{n.name}({args})" + (f": {doc[:140]}" if doc else "")
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            out[n.target.id] = f"{n.target.id} (attribute)"
    init = next((x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == "__init__"), None)
    if init is not None:                       # its self.<name> = ... attributes (locators) are usable too
        for t in ast.walk(init):
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self" \
                    and isinstance(t.ctx, ast.Store):
                out.setdefault(t.attr, f"{t.attr} (attribute)")
    return out


def page_classes(folder: Path) -> dict[str, tuple[str, dict[str, str]]]:
    """class name -> (module, methods) for every project class the journey's tests and conftests import."""
    names: dict[str, str] = {}
    for f in list(folder.glob("test_*.py")) + _conftests(folder):
        names.update(_imports(_parse(f)))
    out = {}
    for n, mod in names.items():
        f = _module_file(mod)
        if f and n in classes_in(f):
            out[n] = (mod, class_methods(n, mod))
    return out


def _example(folder: Path, words: set[str]) -> str:
    best, score = None, -1
    for f in folder.glob("test_*.py"):
        if f.name.startswith("test_studio_"):
            continue
        s = len(words & set(re.findall(r"[a-z]{4,}", f.read_text(encoding="utf-8").lower())))
        if s > score:
            best, score = f, s
    if not best:
        return ""
    return f"# {best.relative_to(e2e.E2E).as_posix()}\n" + "\n".join(best.read_text(encoding="utf-8").split("\n")[:140])


def _spec_lines(pack: str, sid: str, words: set[str]) -> str:
    f = e2e.E2E / "specs" / pack if pack else None
    if not f or not f.exists():
        return ""
    lines = f.read_text(encoding="utf-8").split("\n")
    keep = sorted({j for i, ln in enumerate(lines) if (sid and sid in ln) or len(words & set(re.findall(r"[a-z]{5,}", ln.lower()))) >= 3
                   for j in range(max(0, i - 2), min(len(lines), i + 3))})
    return "\n".join(lines[i] for i in keep[:80])


# ------------------------------------------------------------------ checks

def check_code(code: str, fixtures: dict[str, str], classes: dict[str, tuple[str, dict[str, str]]]) -> list[str]:
    """Static checks: the problems as plain lines (empty = fine)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Python syntax error line {e.lineno}: {e.msg}"]
    probs = []
    if not re.search(r"pytestmark\s*=\s*\[[^\]]*journey\(", code):
        probs.append("pytestmark with pytest.mark.journey(...) is missing")
    tests = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    if not tests:
        probs.append("no test_ function")
    known = set(fixtures) | PYTEST_BUILTIN_FIXTURES
    imported = _imports(tree)
    for t in tests:
        for a in t.args.args:
            if a.arg not in known:
                probs.append(f"{t.name}: argument {a.arg!r} is not a fixture of this journey")
        body = ast.unparse(t)
        if re.search(r"\bpytest\.skip\(|time\.sleep\(", body):
            probs.append(f"{t.name}: uses pytest.skip/time.sleep")
        if re.search(r"\b(?:input_value|inner_text|text_content)\([^)]*\)\.(?:upper|lower|strip)\(\)", body):
            probs.append(f"{t.name}: changes what the app shows (.upper/.lower/.strip) before asserting it")
        if not re.search(r"\bexpect\(|\bassert\b|\.expect_\w+\(", body):
            probs.append(f"{t.name}: checks nothing (no expect / assert)")
    # which class each local name holds: fixture annotations and Class(...) assignments
    holds: dict[str, str] = {}
    fix_type = {n: (re.search(r"-> ([\w.]+)", sig) or [None, ""])[1] for n, sig in fixtures.items()}
    for t in tests:
        for a in t.args.args:
            ann = ast.unparse(a.annotation) if a.annotation else fix_type.get(a.arg, "")
            if ann.split(".")[-1] in classes:
                holds[a.arg] = ann.split(".")[-1]
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            cname = ast.unparse(n.value.func).split(".")[-1]
            if cname in classes:
                holds[n.targets[0].id] = cname
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in holds:
            methods = classes[holds[n.value.id]][1]
            if methods and n.attr not in methods:
                probs.append(f"{holds[n.value.id]} has no method or attribute {n.attr!r}")
    for name, mod in imported.items():
        f = _module_file(mod)
        if not f:
            probs.append(f"import from {mod!r}: no such module")
        elif name not in classes_in(f) and not re.search(
                rf"^(?:def|class)\s+{re.escape(name)}\b|^{re.escape(name)}\s*[:=]", f.read_text(encoding="utf-8"), re.M):
            probs.append(f"{name!r} is not defined in {mod}")
    return sorted(set(probs))


def collect(path: Path) -> str:
    """'' when pytest collects the file in the scripts' own environment, else the error (last lines)."""
    if not e2e.PY.exists():
        return ""                                    # no scripts environment here: static checks only
    try:
        r = subprocess.run([str(e2e.PY), "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                            str(path.relative_to(e2e.E2E))], cwd=str(e2e.E2E), env=e2e.script_env(),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"pytest could not run: {e}"
    if r.returncode == 0:
        return ""
    tail = [ln for ln in (r.stdout + r.stderr).split("\n") if ln.strip() and "Warning" not in ln]
    return "\n".join(tail[-14:])


# ------------------------------------------------------------------ writing

SYSTEM = """You are a senior SDET writing one pytest + Playwright (sync API) test module for the MargBooks e2e project.
Follow the project rules exactly:
- Use ONLY the fixtures listed (most journeys give a ready page-object fixture; use it) and ONLY the page-object
  classes and methods listed. Never invent a method, fixture, module or locator helper. If a step needs something no
  page object offers, use Playwright on the page the fixtures give (page.get_by_role / get_by_label / get_by_text +
  expect), never CSS/XPath, never time.sleep or pytest.skip.
- Module layout: a module docstring (title, "Scenario: scenarios/<pack> <id>. Test case: <TC id>." and one line that
  it was written by Test Studio AI), imports, `pytestmark = [pytest.mark.<priority>, pytest.mark.journey("<journey>")]`
  exactly as given, then one test function per case (usually one) with type hints and a one-line docstring naming the
  scenario id. Arrange / act / assert; asserts with expect() or the page objects' expect_* methods.
- The test must check the case's expected result, not just open a screen. Never weaken an expected value: no
  .upper()/.lower()/strip tricks on what the app shows, no "<=" where the case says "=", no try/except around an
  assert, no `if x.is_visible()` around a step the case requires (only around a popup the case says may appear).
- Navigation: use the fixture's page object / helper that opens the screen when one exists; else the menu by role.
- Where you had to guess (a key, a label, a message text), keep the step but list it in "unsure".
- Copy the style of the example test.
Return JSON: {"code": "<the whole python module>", "unsure": ["<what you could not confirm>", ...]}"""


def _case_block(c, det: dict, sid: str, pack: str) -> str:
    from ui_studio import tests
    steps = det.get("steps") or tests.text_test(c)
    return "\n".join([
        f"Test case {c.id}: {c.title}", f"Scenario: {pack} {sid}".strip(), f"Priority: {c.priority}",
        "Before you start:", *[f"- {x}" for x in det.get("preconditions") or []],
        "Steps:", *[f"{i}. {x}" for i, x in enumerate(steps, 1)],
        "Expected:", *[f"- {x}" for x in (det.get("expected") or c.expected or [])],
        "Refs:", *[f"- {x}" for x in (det.get("refs") or [])[:8]]])


def write(c, folder: Path, path: Path, fn: str, mark_line: str, sid: str, pack: str, progress=None) -> dict:
    """Write an AI test for case c to path. Returns {"ok", "notes", "tokens"}; on ok=False nothing is written.
    progress(stage, step) is told what is happening (step 1-4), for the screen."""
    from ui_studio import tests
    say = progress or (lambda stage, step: None)
    say("Reading the test case, this journey's fixtures and page objects", 1)
    det = tests.case_details().get(c.id) or {}
    words = set(re.findall(r"[a-z]{5,}", (c.title + " " + " ".join(det.get("steps") or [])).lower()))
    fixtures = fixtures_of(folder)
    classes = page_classes(folder)
    ctx = "\n\n".join([
        "CASE\n" + _case_block(c, det, sid, pack),
        f"FILE TO WRITE: {path.relative_to(e2e.E2E).as_posix()}  (test function name: {fn})\nMARKERS LINE: {mark_line}",
        "FIXTURES (name(args) -> type: doc)\n" + "\n".join(fixtures.values()),
        "PAGE OBJECTS (import from module; methods)\n" + "\n".join(
            f"{n}  (from {mod} import {n})\n" + "\n".join(f"    .{m}" for m in ms.values()) for n, (mod, ms) in classes.items()),
        "SPEC LINES\n" + _spec_lines(pack, sid, words),
        "EXAMPLE TEST OF THIS JOURNEY\n" + _example(folder, words)])[:MAX_CTX]
    tokens, notes, last, code = 0, [], "", ""
    for attempt in (1, 2, 3):
        user = ctx if not last else ctx + (f"\n\nYOUR PREVIOUS ANSWER FAILED THESE CHECKS, fix them and answer with the "
                                          f"JSON object only:\n{last}\n\nPREVIOUS CODE:\n{code}")
        say(f"AI is writing the test (try {attempt} of 3)" + (": fixing what the checks found" if last else ""), 2)
        try:
            ans, tok, _ = state.ai_json("write_script", SYSTEM, user, max_tokens=6000, case_id=c.id)
        except state.AIBlocked:
            raise
        except Exception as e:  # noqa: BLE001  (the model answered with prose instead of JSON, provider hiccup)
            last = f"the answer was not the JSON object asked for ({str(e)[:160]})"
            continue
        tokens += tok
        code = str((ans or {}).get("code") or "")
        notes = [str(x) for x in (ans or {}).get("unsure") or []][:8]
        say("Checking the code: Python, fixtures and page-object methods", 3)
        probs = check_code(code, fixtures, classes)
        if c.id not in code:                           # the catalogue links the script to its case by this id
            probs.append(f"the module docstring must say 'Test case: {c.id}.'")
        if not probs:
            path.write_text(code.rstrip() + "\n", encoding="utf-8")
            say("pytest is checking that the test loads", 4)
            err = collect(path)
            if not err:
                return {"ok": True, "notes": notes, "tokens": tokens, "attempts": attempt}
            path.unlink(missing_ok=True)
            probs = [f"pytest --collect-only failed:\n{err}"]
        last = "\n".join(probs)
    return {"ok": False, "notes": [f"The AI script did not pass the checks: {last[:600]}"], "tokens": tokens}
