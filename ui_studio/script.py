"""
Scripts: written lines -> .spec.ts text, .spec.ts text -> YAML steps, Chrome Recorder JSON.

The script text is what the tester sees, verifies and edits. Replay runs the
project's own YAML step runner, so the script is converted to steps first.
Every line that generate() writes is understood again by to_steps(); lines from
Playwright codegen go through ui/codegen_import.py. A line that neither can read is
returned in "unknown" and is never guessed.
"""
from __future__ import annotations

import json
import re

from ui_studio import grammar, memory

_S = r"""'((?:[^'\\]|\\.)*)'"""
HELPERS = {"login": "login", "open": "openScreen", "party": "setParty", "item": "addItem",
           "save": "saveForm", "close": "closeForm", "bulk": "randomSaleBills"}

# A login test checks the login screen itself (wrong password, unknown user...). Its recorded login steps stay in
# the script; the runner signs out first (sign_out) so the test starts on the login page. The real password never
# stays in it: a typed known password becomes process.env.MB_PASS! ({{config_password}} when it runs).
LOGIN_TEST_MARK = "// studio: login test - the recorded login steps are kept; the runner signs out first"
_ENV_VALUE = {"MB_PASS": "{{config_password}}", "MB_USER": "{{config_user}}"}


def is_login_test(code: str) -> bool:
    return "// studio: login test" in (code or "")


def mark_login_test(code: str) -> str:
    """Put the login-test mark on the script (once), right before the first action."""
    if is_login_test(code):
        return code
    ls = (code or "").split("\n")
    at = next((i for i, ln in enumerate(ls) if ln.strip().startswith("await")), len(ls))
    ind = re.match(r"\s*", ls[at]).group() if at < len(ls) else "  "
    ls.insert(at, ind + LOGIN_TEST_MARK)
    return "\n".join(ls)


def q(v) -> str:
    return str(v).replace("\\", "\\\\").replace("'", "\\'")


def unq(v: str) -> str:
    return re.sub(r"\\(.)", r"\1", v)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "test"


# ------------------------------------------------------------- generate

def generate(name: str, module: str, author: str, lines: list[str], tid: str = "") -> dict:
    M = grammar.Memory()
    results, _ = grammar.parse_all(lines, M)
    if any(r["status"] == "bad" for r in results):
        raise ValueError("Fix the red lines first.")
    body, used = [], set()
    for ln, r in zip(lines, results):
        if r["status"] in ("empty", "note"):
            continue
        k, f = r["kind"], r.get("field")
        body.append(f"  // {ln.strip()}")
        if k == "login":
            body.append("  await login(page);"); used.add("login")
        elif k == "open":
            body.append(f"  await openScreen(page, '{q(r['screen_key'])}');"); used.add("openScreen")
        elif k in ("pick", "search") and f["name"] in ("Party Name", "Ledger Name"):
            if k == "search":
                body.append(f"  await page.locator('{q(f['sel'])}').fill('{q(r['value'])}');")
            else:
                body.append(f"  await setParty(page, '{q(r['value'])}');"); used.add("setParty")
        elif k in ("pick", "search", "fill"):
            body.append(f"  await page.locator('{q(f['sel'])}').fill('{q(r['value'])}');")
            if k == "pick":
                body.append("  await page.keyboard.press('Enter');")
        elif k == "item":
            cols = {x["field"]["name"]: x["value"] for x in r.get("extras", [])}
            parts = [f"item: '{q(r['value'])}'", f"qty: '{q(cols.get('Qty', r.get('qty', '')))}'"]
            if "Rate" in cols:
                parts.append(f"rate: '{q(cols['Rate'])}'")
            if "Disc 1.%" in cols:
                parts.append(f"discount: '{q(cols['Disc 1.%'])}'")
            body.append(f"  await addItem(page, {{ {', '.join(parts)} }});"); used.add("addItem")
        elif k == "click":
            if f["name"] == "Save":
                body.append("  await saveForm(page);"); used.add("saveForm")
            elif f["name"] == "Close":
                body.append("  await closeForm(page);"); used.add("closeForm")
            else:
                body.append(f"  await page.locator('{q(f['sel'])}').click();")
        elif k == "verify":
            body.append(f"  await expect(page.getByText('{q(r['what'])}')).toBeVisible();")
        elif k == "wait":
            body.append(f"  await page.waitForTimeout({r['secs'] * 1000}); // wait (asked in the steps)")
        elif k == "key":
            body.append(f"  await page.keyboard.press('{q(r['key'])}');")
        elif k == "bulk":
            body.append(f"  await randomSaleBills(page, {{ bills: {r['count']}, itemsPerBill: {r['items']} }});")
            used.add("randomSaleBills")
    head = [f"// {tid or 'TC-new'} · {name or 'Untitled case'} · module: {module or '-'}",
            f"// Written by: {author or '-'}",
            "import { test, expect } from '@playwright/test';"]
    if used:
        head.append(f"import {{ {', '.join(sorted(used))} }} from '../helpers/mb';")
    code = "\n".join(head + ["", f"test('{q(name or 'Untitled case')}', async ({{ page }}) => {{"] + body + ["});", ""])
    return {"code": code, "actions": count_actions(code), "file": "written.spec.ts"}


def count_actions(code: str) -> int:
    return sum(1 for ln in code.split("\n") if ln.strip().startswith("await"))


# ------------------------------------------------------------- login block
#
# A recording that starts before sign-in contains the whole login: the login page,
# the e-mail, the password, the eye icon, arrow keys inside the password box...
# MargBooks' password box has no name or placeholder, so codegen writes it as a bare
# getByRole('textbox') and nothing says "password". The runner signs in by itself
# before every test, so the whole block is replaced by login(page).

_LOGIN_START = re.compile(
    r"\.goto\(\s*'[^']*(?:accounts\.margbooks|/login)|"
    r"getBy(?:Role|Placeholder|Label)\([^)]*'(?:Email address[^']*|[^']*mobile number|User ID|Password|PIN|OTP)'|"
    r"type=\"?password", re.I)
_LOGIN_MORE = re.compile(
    r"name: '(?:Login|Log in|Sign in|Continue|Next|Submit|Verify|Proceed)'|"
    r"getByRole\('(?:textbox|img|button|checkbox)'\)(?:\.(?:nth\(\d+\)|first\(\)|last\(\)))?\.(?:click|fill|press|check)\(|"
    r"\.goto\(\s*'https?://[^/']+/?'\s*\)", re.I)


def _company_words() -> list[str]:
    try:
        from config.settings import settings
        comp = (settings.COMPANY or "").split(" (")[0].strip()
        return [comp] if len(comp) > 3 else []
    except Exception:  # noqa: BLE001
        return []


# A typed value: the password step of a login (MargBooks' password box is a bare textbox, or it says Password/PIN).
_LOGIN_SECRET = re.compile(
    r"getByRole\('textbox'\)(?:\.(?:nth\(\d+\)|first\(\)|last\(\)))?\.fill\(|"
    r"(?:Password|PIN|OTP)[^)]*\)[^;]*\.fill\(|type=\"?password[^;]*\.fill\(", re.I)
_LOGIN_GAP = 3          # unknown steps (e.g. a 'Login with password' link) allowed inside a login before the password
_LOGIN_GAP_MAX = 8      # a longer run of unknown steps stays in the login only when the password fill ends it
_LOGIN_GAP_LIMIT = 40   # ... and beyond that only plain clicks (links, tabs) do, up to this many
# A typed literal right before the login's submit (Continue / Login...) is the password too, whatever locator the
# box has (a CSS id, locator('input').nth(1)...): MargBooks' boxes change, the submit button does not.
_FILL_LITERAL = re.compile(r"\.fill\(\s*'[^']*'\s*\)")
_LOGIN_SUBMIT = re.compile(r"name: '(?:Login|Log in|Sign in|Continue|Next|Submit|Verify|Proceed)'|\.press\('Enter'\)",
                           re.I)
_LOGIN_SUBMIT_BTN = re.compile(r"name: '(?:Login|Log in|Sign in|Continue|Verify)'", re.I)


def single_quotes(code: str) -> str:
    """JS strings in "..." (or `...` without ${}) written as '...'. Codegen writes single quotes and every rule of
    the Studio (login block, password redaction, Verify, to_steps) reads them; a script re-formatted by Prettier or
    VS Code format-on-save before pasting had double quotes, and its whole login and password stayed in it.
    A string that holds a ' or a backslash escape is left as it is."""
    out, i, n = [], 0, len(code)
    while i < n:
        ch = code[i]
        if ch == "/" and i + 1 < n and code[i + 1] == "/":          # a // comment: up to the end of the line
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append(code[i:j])
            i = j
            continue
        if ch in "'\"`":
            j = i + 1
            while j < n and code[j] != ch and not (ch != "`" and code[j] == "\n"):
                j += 2 if code[j] == "\\" else 1
            body = code[i + 1:j]
            if ch != "'" and j < n and code[j] == ch and "'" not in body and "\\" not in body \
                    and "\n" not in body and "${" not in body:
                out.append("'" + body + "'")
            else:
                out.append(code[i:j + 1])
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def is_secret(ln: str, nxt: str = "", submit: re.Pattern | None = None) -> bool:
    """A typed value of the login: the password box (bare textbox, Password/PIN/OTP), or a literal typed right
    before the login's submit step `nxt`. Both lines in single quotes (single_quotes)."""
    if _LOGIN_SECRET.search(ln):
        return True
    if _LOGIN_START.search(ln):          # the e-mail / user id box: typed, but not the password
        return False
    return bool(_FILL_LITERAL.search(ln) and (submit or _LOGIN_SUBMIT).search(nxt or ""))


def login_block(code: str) -> set[int]:
    """0-based indexes of the lines that belong to a recorded login.

    Until the password has been typed the login is not over: a few steps the rules do not know (a 'Login with
    password' link, a 'Remember me' box...) stay in the block when a login step follows them. Without this, the
    block ended at the unknown step and the password typed after it stayed in the script."""
    comp = _company_words()
    out: set[int] = set()
    inside, typed, gap = False, False, []
    # detection reads every line in single quotes (a pasted, re-formatted script may use double quotes)
    awaits = [(i, single_quotes(raw.strip())) for i, raw in enumerate(code.split("\n"))
              if raw.strip().startswith("await")]
    for k, (i, ln) in enumerate(awaits):
        nxt = awaits[k + 1][1] if k + 1 < len(awaits) else ""
        secret = is_secret(ln, nxt) if not typed else bool(_LOGIN_SECRET.search(ln))
        if _LOGIN_START.search(ln):
            if len(gap) <= _LOGIN_GAP or secret:
                out.update(gap)
            inside = True
            gap = []
        elif inside and secret and not typed:
            out.update(gap)                  # the password, after steps the rules do not know: all login steps
            gap = []
        elif inside and not (_LOGIN_MORE.search(ln) or any(c in ln for c in comp)):
            plain_click = ".click(" in ln and ".goto(" not in ln and ".fill(" not in ln
            if not typed and (len(gap) < _LOGIN_GAP_MAX or (plain_click and len(gap) < _LOGIN_GAP_LIMIT)):
                gap.append(i)            # maybe part of the login: decided by the next step
                continue
            inside, gap = False, []
        elif inside and gap:
            if len(gap) > _LOGIN_GAP and not secret:
                inside, gap = False, []      # many unknown steps and no password after them: the login was over
            else:
                out.update(gap)              # the password typed after them: they were login steps (no password kept)
                gap = []
        if inside:
            out.add(i)
            if secret:
                typed = True
        else:
            typed = False
    return out


def replace_login(code: str) -> str:
    """Swap the recorded login for one login(page) line, so no password stays in the script."""
    if is_login_test(code):              # a login test keeps its login steps (passwords are cleaned by redact)
        return code
    idx = login_block(code)
    if not idx:
        return code
    ls = code.split("\n")
    first = min(idx)
    keep = []
    for i, ln in enumerate(ls):
        if i == first:
            keep.append("  await login(page);   // reads MB_USER / MB_PASS")
        if i not in idx:
            keep.append(ln)
    code = "\n".join(keep)
    if not re.search(r"import \{[^}]*\blogin\b[^}]*\} from '\.\./helpers/mb';", code):
        anchor = re.search(r"import \{[^}]*\} from '@playwright/test';", code)
        line = "import { login } from '../helpers/mb';"
        code = code.replace(anchor.group(0), anchor.group(0) + "\n" + line, 1) if anchor else line + "\n" + code
    return code


# ---------------------------------------------------------- to YAML steps

def to_steps(code: str) -> dict:
    """Script text -> {"steps": [...], "unknown": [{"line","text","why"}]}."""
    from ui import codegen_import
    steps: list[dict] = []
    unknown: list[dict] = []
    note = ""
    login_test = is_login_test(code)
    login_idx = set() if login_test else login_block(code)
    if login_test:
        steps.append({"action": "sign_out", "note": "Sign out and open the login page (login test)", "_line": 0})
    started = False
    for n, raw in enumerate(code.split("\n"), 1):
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith("//"):
            if not ln.startswith("// studio: login test"):
                note = ln[2:].strip()
            continue
        if not ln.startswith("await"):
            continue
        # a comment after the statement ("await login(page);   // reads MB_USER") is not part of it
        ln = re.sub(r";\s*//[^'\"]*$", ";", ln)
        if login_test:
            if not started and ".goto(" in ln:      # the start page: sign_out already opened the login page
                note = ""
                continue
            started = True
            if re.fullmatch(r"await login\(page\);", ln):
                unknown.append({"line": n, "text": ln[:110],
                                "why": "A login test types its own login. Remove login(page), or remove the "
                                       "'studio: login test' line to make it a normal test."})
                continue
            # process.env.MB_PASS! / MB_USER!: the runner's own login, filled in when the step runs
            shown = ln
            ln = re.sub(r"process\.env\.(MB_PASS|MB_USER)!?", lambda m: "'" + _ENV_VALUE[m.group(1)] + "'", ln)
            if ln != shown and not note:
                note = shown[:110]
            # MargBooks' password box has no name: codegen writes a bare getByRole('textbox'). On the login page
            # that is the password field (login.password in the locator file).
            m = re.fullmatch(r"await page\.(?:getByRole\('textbox'\)(?:\.(?:first|last)\(\)|\.nth\(\d+\))?|"
                             r"getBy(?:Label|Placeholder)\('(?:Password|PIN)[^']*'\)|"
                             r"locator\('input\[type=\"?password\"?\]'\))"
                             r"\.(fill|press|click|dblclick)\((?:" + _S + r")?[^)]*\);", ln)
            if m:
                act = {"fill": "fill", "press": "press"}.get(m.group(1), "click")
                st = {"action": act, "target": "login.password", "note": note or shown[:110], "_line": n}
                if act != "click":
                    st["value"] = unq(m.group(2) or "")
                steps.append(st)
                note = ""
                continue
        if n - 1 in login_idx:          # recorded login: the runner signs in itself
            if not any(s.get("_login") for s in steps):
                steps.append({"action": "note", "value": "Log in (the runner signs in before every test)",
                              "note": "Log in", "_line": n, "_login": True})
            note = ""
            continue
        step = _helper_step(ln) or _env_step(ln)
        if step == "skip":
            continue
        if step is None:
            step = _keyboard(ln, steps)
            if step == "skip":
                continue
        if step is None:
            if not login_test and (re.search(r"getByPlaceholder\('(User ID|Password)'\)|type=\"?password", ln, re.I)
                                   or re.search(r"name: 'Login'", ln)):
                unknown.append({"line": n, "text": ln[:110],
                                "why": "Login is done by the runner. Replace the login lines with login(page)."})
                continue
            step = codegen_import._one(ln)
        if step:
            step.setdefault("note", note or ln[:110])
            step["_line"] = n            # script line, so a failing step can be located; never saved to YAML
            steps.append(step)
        else:
            unknown.append({"line": n, "text": ln[:110], "why": "This action cannot be replayed."})
        note = ""
    if login_test and len(steps) == 1:
        steps = []                       # only the sign-out: the script has no actions
    return {"steps": _merge_party(steps), "unknown": unknown, "login_test": login_test}


def _merge_party(steps: list[dict]) -> list[dict]:
    """A party typed in a search step and then picked is one step, not two."""
    out: list[dict] = []
    for st in steps:
        prev = out[-1] if out else None
        if st["action"] == "set_party" and prev and prev["action"] == "fill" \
                and prev.get("value") == st.get("value") and _is_party_sel(prev.get("target", "")):
            out.pop()
        out.append(st)
    return out


def _is_party_sel(sel: str) -> bool:
    return bool(re.search(r"ledgerName|LedgerName|partyLinkId", sel))


def _helper_step(ln: str):
    if re.fullmatch(r"await login\(page\);", ln):
        return {"action": "note", "value": "Log in (the runner signs in before every test)"}
    m = re.fullmatch(rf"await openScreen\(page, {_S}\);", ln)
    if m:
        return {"action": "open_screen", "target": unq(m.group(1))}
    m = re.fullmatch(rf"await setParty\(page, {_S}\);", ln)
    if m:
        return {"action": "set_party", "value": unq(m.group(1))}
    m = re.fullmatch(r"await addItem\(page, \{(.*)\}\);", ln)
    if m:
        kv = {k: unq(v) for k, v in re.findall(rf"(\w+):\s*{_S}", m.group(1))}
        parts = [kv.get("item", ""), kv.get("qty", ""), kv.get("rate", ""), kv.get("discount", "")]
        while parts and parts[-1] == "":
            parts.pop()
        return {"action": "add_item", "value": " | ".join(parts)}
    if ln == "await saveForm(page);":
        return {"action": "save_form"}
    if ln == "await closeForm(page);":
        return {"action": "close_form"}
    m = re.fullmatch(r"await randomSaleBills\(page, \{ bills: (\d+), itemsPerBill: (\d+) \}\);", ln)
    if m:
        return {"action": "bulk_sale_bills", "value": f"{m.group(1)} | {m.group(2)}", "destructive": True}
    m = re.fullmatch(rf"await page\.locator\({_S}\)\.fill\({_S}\);", ln)
    if m:
        return {"action": "fill", "target": unq(m.group(1)), "value": unq(m.group(2))}
    m = re.fullmatch(rf"await page\.locator\({_S}\)\.fill\(today\(\)\);", ln)
    if m:
        return {"action": "fill", "target": unq(m.group(1)), "value": "{{today}}"}
    m = re.fullmatch(rf"await page\.locator\({_S}\)\.click\(\);", ln)
    if m:
        return {"action": "click", "target": unq(m.group(1))}
    m = re.fullmatch(rf"await page\.locator\({_S}\)\.press\({_S}\);", ln)
    if m:
        return {"action": "press", "target": unq(m.group(1)), "value": unq(m.group(2))}
    m = re.fullmatch(r"await page\.waitForTimeout\((\d+)\);.*", ln)
    if m:
        return {"action": "sleep", "value": str(round(int(m.group(1)) / 1000, 2)).rstrip("0").rstrip(".")}
    m = re.fullmatch(rf"await expect\(page\.getByText\({_S}\)\)\.toBeVisible\(\);", ln)
    if m:
        return {"action": "assert_text", "value": unq(m.group(1))}
    return None


def _env_step(ln: str):
    if "MB_COMPANY" in ln:
        return {"action": "note", "value": "Company is chosen by the runner login"}
    return None


def _keyboard(ln: str, steps: list[dict]):
    m = re.fullmatch(rf"await page\.keyboard\.press\({_S}\);", ln)
    if not m:
        return None
    key = unq(m.group(1))
    if key == "Enter" and steps and steps[-1]["action"] in ("set_party", "add_item", "note"):
        return "skip"        # those steps already press Enter themselves
    if key == "Enter" and steps and steps[-1].get("target"):
        return {"action": "press", "target": steps[-1]["target"], "value": key}
    return {"action": "press", "value": key}      # F10, Alt+N, Escape...: a key on the page, no target


# ------------------------------------------------------- Chrome Recorder

def recorder_json(title: str, app_url: str, steps: list[dict], screen_routes: dict | None = None) -> str:
    """Chrome DevTools Recorder export, importable and replayable in DevTools -> Recorder."""
    M = grammar.Memory()
    party = _find_sel(M, "Party Name") or _find_sel(M, "Ledger Name")
    out = {"title": title, "steps": [
        {"type": "setViewport", "width": 1366, "height": 768, "deviceScaleFactor": 1,
         "isMobile": False, "hasTouch": False, "isLandscape": False},
        {"type": "navigate", "url": app_url, "assertedEvents": [{"type": "navigation", "url": app_url, "title": ""}]}]}
    S = out["steps"]

    def sels(sel: str):
        return [[sel]] if sel else []

    def put(sel, value, enter=False):
        S.append({"type": "click", "target": "main", "selectors": sels(sel), "offsetX": 8, "offsetY": 8})
        S.append({"type": "change", "target": "main", "selectors": sels(sel), "value": str(value)})
        if enter:
            S.append({"type": "keyDown", "target": "main", "key": "Enter"})
            S.append({"type": "keyUp", "target": "main", "key": "Enter"})

    for st in steps:
        a, t, v = st.get("action"), st.get("target"), st.get("value")
        if a == "open_screen" and screen_routes and screen_routes.get(t):
            S.append({"type": "navigate", "url": app_url.rstrip("/") + screen_routes[t]})
        elif a == "fill":
            put(t, v)
        elif a == "set_party" and party:
            put(party, v, enter=True)
        elif a == "add_item":
            parts = [x.strip() for x in str(v).split("|")]
            put('[id^="txt-tmp_barcode-"]', parts[0], enter=True)
            for i, col in ((1, "txt-unitToEnteredValue"), (2, "txt-salePurchaseRate"), (3, "txt-discount1")):
                if len(parts) > i and parts[i]:
                    put(f'[id^="{col}-"]', parts[i])
        elif a == "click":
            S.append({"type": "click", "target": "main", "selectors": sels(t), "offsetX": 8, "offsetY": 8})
        elif a == "save_form":
            S.append({"type": "click", "target": "main", "selectors": [['[id^="btnSave"]']], "offsetX": 8, "offsetY": 8})
        elif a == "assert_text":
            S.append({"type": "waitForElement", "target": "main", "selectors": [[f"text/{v}"]]})
    return json.dumps(out, indent=2)


def _find_sel(M: grammar.Memory, name: str) -> str:
    for s in M.screens.values():
        for f in s["fields"]:
            if f["name"] == name and f["kind"] != "grid":
                return f["sel"]
    return ""
