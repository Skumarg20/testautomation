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


# ---------------------------------------------------------- to YAML steps

def to_steps(code: str) -> dict:
    """Script text -> {"steps": [...], "unknown": [{"line","text","why"}]}."""
    from ui import codegen_import
    steps: list[dict] = []
    unknown: list[dict] = []
    note = ""
    for n, raw in enumerate(code.split("\n"), 1):
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith("//"):
            note = ln[2:].strip()
            continue
        if not ln.startswith("await"):
            continue
        step = _helper_step(ln) or _env_step(ln)
        if step == "skip":
            continue
        if step is None:
            step = _keyboard(ln, steps)
            if step == "skip":
                continue
        if step is None:
            if re.search(r"getByPlaceholder\('(User ID|Password)'\)|type=\"?password", ln, re.I) \
                    or re.search(r"name: 'Login'", ln):
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
    return {"steps": _merge_party(steps), "unknown": unknown}


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
    if steps and steps[-1]["action"] in ("set_party", "add_item", "note"):
        return "skip"        # those steps already press Enter themselves
    if steps and steps[-1].get("target"):
        return {"action": "press", "target": steps[-1]["target"], "value": unq(m.group(1))}
    return None


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
