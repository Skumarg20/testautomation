"""
Verify script: local rules first (free), AI only for what rules cannot judge.

Each finding has a severity (Must fix / Should fix / Nice to have), a source
(Local check / Project rules / App memory / AI), a plain-English reason, and a
diff (old lines -> new lines). "manual" means the rule found a problem but has
no safe automatic replacement; the tester edits it by hand.

Rules (all local, 0 tokens):
  login      password / user id / login steps written in the script   -> login(page)
  wait       fixed waitForTimeout (not one the tester asked for)      -> removed
  company    company name typed in the script                         -> process.env.MB_COMPANY
  position   nth-child, .nth(n), #mat-input-7 style locators          -> stable locator from memory
  dup        same text typed twice (search + select)                  -> typed once
  date       fixed bill date                                          -> today()   (nice to have)
  name       test named "test"                                        -> meaningful name
  assert     nothing checked after Save                               -> AI proposes the check (or manual)
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable

from ui_studio import grammar, memory, state

SEV = {"Must fix": 0, "Should fix": 1, "Nice to have": 2}
_S = r"""'((?:[^'\\]|\\.)*)'"""
ASKED = "// wait (asked in the steps)"


@dataclass
class Finding:
    id: str
    sev: str
    src: str
    title: str
    why: str
    old: list[str]
    neu: list[str]
    apply: Callable[[str], str]
    tokens: int = 0
    manual: bool = False

    def as_dict(self) -> dict:
        return {"id": self.id, "sev": self.sev, "src": self.src, "tokens": self.tokens, "title": self.title,
                "why": self.why, "old": self.old, "neu": self.neu, "manual": self.manual}


def _h(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:6]


def _add_import(code: str, name: str, frm: str) -> str:
    """Add `name` to an existing import from `frm`, or add a new import line."""
    m = re.search(rf"import \{{([^}}]*)\}} from '{re.escape(frm)}';", code)
    if m:
        names = [x.strip() for x in m.group(1).split(",") if x.strip()]
        if name in names:
            return code
        names.append(name)
        return code.replace(m.group(0), f"import {{ {', '.join(sorted(names))} }} from '{frm}';")
    anchor = re.search(r"import \{[^}]*\} from '@playwright/test';", code)
    line = f"import {{ {name} }} from '{frm}';"
    if anchor:
        return code.replace(anchor.group(0), anchor.group(0) + "\n" + line, 1)
    return line + "\n" + code


def _env() -> dict:
    try:
        from ui import envs
        return envs.apply_active() or {}
    except Exception:  # noqa: BLE001
        return {}


# ---------------------------------------------------------------- rules

LOGIN_LINE = re.compile(
    r"goto\([^)]*login|getByPlaceholder\('(User ID|Password|Email address[^']*)'\)|getByLabel\('(User ID|Password)'|"
    r"name: '(Login|SIGN IN|CONTINUE)'|exact_text=|MB_COMPANY|type=\"?password", re.I)


def r_login(code: str, ctx: dict):
    lines = code.split("\n")
    env = _env()
    secret = [v for v in (env.get("password"), env.get("user")) if v and len(v) > 3]
    has_pw = any(re.search(r"password", ln, re.I) and ".fill(" in ln for ln in lines) \
        or any(s in code for s in secret)
    if not has_pw or "await login(page)" in code:
        return None
    idx = [i for i, ln in enumerate(lines)
           if ln.strip().startswith("await") and (LOGIN_LINE.search(ln) or any(s in ln for s in secret))]
    comp = (env.get("company") or "").split(" (")[0].strip()
    if comp:
        idx += [i for i, ln in enumerate(lines) if comp in ln and ln.strip().startswith("await")]
    idx = sorted(set(idx))
    if not idx:
        return None

    def apply(c: str) -> str:
        ls = c.split("\n")
        keep = [ln for i, ln in enumerate(ls) if i not in idx]
        keep.insert(idx[0] - sum(1 for j in idx if j < idx[0]), "  await login(page);   // reads MB_USER / MB_PASS")
        return _add_import("\n".join(keep), "login", "../helpers/mb")
    return Finding("login", "Must fix", "Project rules", "Password is written in the script",
                   "The login steps contain the user id and password. The project already has a login helper "
                   "that reads them from Settings.", [lines[i] for i in idx],
                   ["  await login(page);   // reads MB_USER / MB_PASS"], apply)


def r_wait(code: str, ctx: dict):
    bad = [ln for ln in code.split("\n") if re.search(r"waitForTimeout\(\d+\)", ln) and ASKED not in ln]
    if not bad:
        return None
    return Finding("wait", "Should fix", "Local check", "Fixed wait",
                   "Playwright waits for elements by itself. A fixed wait makes tests slow and still breaks on a slow day.",
                   bad, [], lambda c: "\n".join(ln for ln in c.split("\n") if ln not in bad))


def r_company(code: str, ctx: dict):
    comp = (_env().get("company") or "").split(" (")[0].strip()
    if not comp or "await login(page)" in code:
        return None
    hit = [ln for ln in code.split("\n") if comp in ln and ln.strip().startswith("await")]
    if not hit:
        return None
    new = [ln.replace(f"'{comp}'", "process.env.MB_COMPANY!").replace(comp, "process.env.MB_COMPANY") for ln in hit]
    return Finding("company", "Should fix", "Project rules", "Company name is fixed in the script",
                   "The test fails on any other company. Read it from Settings like the other tests.",
                   hit, new, lambda c: c.replace(f"'{comp}'", "process.env.MB_COMPANY!"))


POS = re.compile(r"nth-child\(|\.nth\(\d+\)|#mat-input-\d+|mat-input-\d+|\.first\(\)\.nth|xpath=/html")


def _screen_of(lines: list[str], upto: int, M: grammar.Memory) -> str | None:
    cur = None
    for ln in lines[:upto]:
        for lit in re.findall(_S, ln):
            s = M.find_screen(lit.replace("\\'", "'"))
            if s:
                cur = s
        m = re.search(r"openScreen\(page, '([^']+)'", ln)
        if m:
            cur = next((n for n, s in M.screens.items() if s["key"] == m.group(1)), cur)
    return cur


def r_position(code: str, ctx: dict):
    lines, M, out = code.split("\n"), grammar.Memory(), []
    for i, ln in enumerate(lines):
        if not ln.strip().startswith("await") or not POS.search(ln):
            continue
        scr = _screen_of(lines, i, M)
        field_ = None
        # A comment written by the Write screen names the field, so the mapping is exact and free.
        prev = next((lines[j] for j in range(i - 1, max(i - 3, -1), -1) if lines[j].strip().startswith("//")), "")
        if scr:
            for f in M.screens[scr]["fields"]:
                if any(re.search(rf"\b{re.escape(a)}\b", prev.lower()) for a in f["aliases"]):
                    field_ = f
                    break
        if not field_ and scr and ctx.get("ai"):
            field_ = _ai_field(lines, i, scr, M, ctx)
        out.append((i, ln, scr, field_))
    if not out:
        return None
    can = [(ln, re.sub(r"page\.(?:locator|getByRole)\([^)]*\)(?:\.nth\(\d+\))?", f"page.locator('{f['sel']}')", ln, 1))
           for _, ln, _, f in out if f]
    title = "Field found by page position" if len(out) == 1 else f"{len(out)} fields found by page position"
    why = ("Position-based locators (nth-child, .nth(n), auto ids like mat-input-7) break when a field is added "
           "or the page re-renders. ")
    why += ("App memory has a stable locator for " + ", ".join(f"{f['name']}" for _, _, _, f in out if f) + "."
            if can else "App memory could not tell which field this is - choose the field and edit the line.")

    def apply(c: str) -> str:
        for o, n in can:
            c = c.replace(o, n)
        return c
    return Finding("pos-" + _h("".join(o for _, o, _, _ in out)), "Must fix",
                   "AI" if ctx.get("ai_used_position") else "App memory", title, why, [o for _, o, _, _ in out],
                   [n for _, n in can] or ["(edit by hand)"], apply, tokens=ctx.get("ai_tokens_position", 0),
                   manual=not can)


def _ai_field(lines, i, scr, M, ctx):
    """Ask AI which field of THIS screen the line means. Only the line, 3 lines before it and field names are sent."""
    names = [f["name"] for f in M.screens[scr]["fields"]]
    snippet = "\n".join(lines[max(0, i - 3): i + 1])
    try:
        ans, tok, _cached = state.ai_json(
            "verify.position", "You map one Playwright line to a field of a screen. Reply JSON {\"field\":\"<exact name from the list or empty>\"}.",
            f"screen: {scr}\nfields: {names}\ncode:\n{snippet}", 300, ctx.get("case_id", ""))
    except Exception as e:  # noqa: BLE001
        ctx["ai_note"] = str(e)
        return None
    ctx["ai_used_position"] = True
    ctx["ai_tokens_position"] = ctx.get("ai_tokens_position", 0) + tok
    name = (ans or {}).get("field", "")
    return next((f for f in M.screens[scr]["fields"] if f["name"] == name), None)   # must exist in memory


DUP = re.compile(r"(  await page\.locator\('((?:[^'\\]|\\.)*)'\)\.fill\('((?:[^'\\]|\\.)*)'\);\n)((?:  //[^\n]*\n)*)"
                 r"(  await (?:setParty\(page, '\3'\);|page\.locator\('\2'\)\.fill\('\3'\);))")


def r_dup(code: str, ctx: dict):
    m = DUP.search(code)
    if not m:
        return None
    return Finding("dup", "Should fix", "Local check", "Search and Select type the same text twice",
                   "The text is typed in the search step and typed again in the select step. Typing once is enough.",
                   [m.group(1).rstrip()], [], lambda c: DUP.sub(lambda mm: mm.group(4) + mm.group(5), c, count=1))


DATE = re.compile(r"(locator\('[^']*[Dd]ate[^']*'\)\.fill\()'(\d\d-\d\d-\d{4})'(\))")


def r_date(code: str, ctx: dict):
    ls = [ln for ln in code.split("\n") if DATE.search(ln)]
    if not ls:
        return None
    return Finding("date", "Nice to have", "Project rules", "Bill date is a fixed date",
                   "A fixed date can fail later (books period, back-date lock). Use today() unless the date itself is tested.",
                   ls, [DATE.sub(r"\1today()\3", ls[0])],
                   lambda c: _add_import(DATE.sub(r"\1today()\3", c), "today", "../helpers/dates"))


def r_name(code: str, ctx: dict):
    m = re.search(r"test\('(test|Test|untitled|Untitled case)',", code)
    if not m:
        return None
    M = grammar.Memory()
    lines = code.split("\n")
    scr = _screen_of(lines, len(lines), M)
    saved = "saveForm" in code or "Save" in code
    name = f"{scr or 'Recorded'} {'save' if saved else 'check'}".strip()
    return Finding("name", "Nice to have", "Local check", "Test is named “test”",
                   "A meaningful name helps everyone find it in Run and Reports. You can change it again when saving.",
                   [m.group(0) + " ..."], [f"test('{name}', ..."], lambda c: c.replace(m.group(0), f"test('{name}',", 1))


def r_assert(code: str, ctx: dict):
    has_save = bool(re.search(r"saveForm\(page\)|name: '[^']*Save[^']*'|btnSave|\[id\^=\"btnSave", code))
    if not has_save or "expect(" in code:
        return None
    lines = code.split("\n")
    last_save = max(i for i, ln in enumerate(lines)
                    if re.search(r"saveForm\(page\)|Save|btnSave", ln) and ln.strip().startswith("await"))
    neu, tok, src, manual, why = None, 0, "Local check", True, (
        "The test passes even if the bill is not saved. Add a check for what the app shows after Save.")
    if ctx.get("ai"):
        try:
            ans, tok, cached = state.ai_json(
                "verify.assert", "Propose ONE Playwright line that checks a success message after Save. "
                "Reply JSON {\"text\":\"message text the app shows\"}.", "\n".join(lines[max(0, last_save - 4): last_save + 1]),
                300, ctx.get("case_id", ""))
            text = re.sub(r"[^\w .,\-]", "", str((ans or {}).get("text", ""))).strip()
            if 2 < len(text) < 60:
                neu, src, manual = f"  await expect(page.getByText('{text}')).toBeVisible();", "AI", False
                why = "The test passes even if the bill is not saved. AI proposed a check for the success message."
        except Exception as e:  # noqa: BLE001
            ctx["ai_note"] = str(e)
    if not neu:
        neu = "  await expect(page.getByText('<message the app shows after Save>')).toBeVisible();"

    def apply(c: str) -> str:
        if manual:
            return c
        ls = c.split("\n")
        k = max(i for i, ln in enumerate(ls) if re.search(r"saveForm\(page\)|Save|btnSave", ln) and ln.strip().startswith("await"))
        ls.insert(k + 1, neu)
        return "\n".join(ls)
    return Finding("assert", "Should fix", src, "Nothing is checked after Save", why, [lines[last_save]],
                   [lines[last_save], neu], apply, tokens=tok, manual=manual)


RULES = [r_login, r_wait, r_company, r_position, r_dup, r_date, r_name, r_assert]


def run(code: str, src: str = "record", case_id: str = "") -> dict:
    s = state.load_settings()
    ai_ok = s["ai_mode"] != "never"
    ctx: dict = {"ai": ai_ok, "case_id": case_id}
    found = [f for rule in RULES if (f := rule(code, ctx))]
    found.sort(key=lambda f: SEV[f.sev])
    ai_tok = sum(f.tokens for f in found)
    return {"findings": [f.as_dict() for f in found], "tokens": {"local": len(RULES), "ai": ai_tok},
            "ai_note": ctx.get("ai_note", "")}


def _findings(code: str, case_id: str = "") -> list[Finding]:
    ctx: dict = {"ai": state.load_settings()["ai_mode"] != "never", "case_id": case_id}
    return [f for rule in RULES if (f := rule(code, ctx))]


def apply(code: str, ids: list[str], case_id: str = "") -> str:
    for fid in ids:
        for f in _findings(code, case_id):
            if f.id == fid and not f.manual:
                code = f.apply(code)
                break
    return code
